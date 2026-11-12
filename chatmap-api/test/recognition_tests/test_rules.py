from types import SimpleNamespace

from recognition.rules import outcomes


def outcome(rules, text, group):
    """What the only rule of a test that a message meets does with it, or None."""
    found = outcomes(rules, text, group)
    assert len(found) <= 1
    return found[0] if found else None


def _rule(conditions, actions, enabled=True, rule_id="r-1", description="North access"):
    return SimpleNamespace(id=rule_id, description=description, enabled=enabled, conditions=conditions, actions=actions)


def _all(*items):
    return {"match": "all", "items": list(items)}


def _any(*items):
    return {"match": "any", "items": list(items)}


def _contains(*values):
    return {"field": "content", "operator": "contains", "values": list(values)}


def _not_contains(*values):
    return {"field": "content", "operator": "not_contains", "values": list(values)}


def _group_is(*values):
    return {"field": "group", "operator": "is", "values": list(values)}


def _group_is_not(*values):
    return {"field": "group", "operator": "is_not", "values": list(values)}


CLOSED = {"type": "suggest_status", "key_id": "k-1", "value_id": "v-closed"}
NORTH = {"type": "suggest_place", "point_id": "p-north"}


def test_a_rule_that_matches_suggests_its_place_and_value():
    rule = _rule(_all(_contains("acceso norte")), [NORTH, CLOSED])

    found = outcome([rule], "Cerrado el ACCESO NORTE desde las 8", "g-1")

    assert (found.rule_id, found.point_id, found.key_id, found.value_id, found.hide) == (
        "r-1", "p-north", "k-1", "v-closed", False,
    )


def test_a_condition_is_met_by_any_of_its_values():
    rule = _rule(_all(_contains("cerrado", "cerrada", "مسكر")), [CLOSED])

    assert outcome([rule], "la ruta está cerrada", "g-1") is not None
    assert outcome([rule], "الحاجز مسكّر", "g-1") is not None
    assert outcome([rule], "abierto", "g-1") is None


def test_a_negated_condition_is_met_by_none_of_its_values():
    rule = _rule(_all(_contains("cerrado"), _not_contains("ya no", "abrieron"), _group_is_not("g-south")), [CLOSED])

    assert outcome([rule], "cerrado el norte", "g-north") is not None
    assert outcome([rule], "ya no está cerrado", "g-north") is None
    assert outcome([rule], "cerrado el norte", "g-south") is None


def test_groups_of_conditions_go_together_as_they_say():
    # (closed or blocked) and (the north group or it says "north")
    rule = _rule(
        _all(_any(_contains("cerrado"), _contains("bloqueado")), _any(_group_is("g-north"), _contains("norte"))),
        [CLOSED],
    )

    assert outcome([rule], "bloqueado", "g-north") is not None
    assert outcome([rule], "cerrado el norte", "g-south") is not None
    assert outcome([rule], "cerrado", "g-south") is None
    assert outcome([rule], "todo bien", "g-north") is None


def test_every_rule_a_message_meets_applies_and_disabled_ones_are_skipped():
    off = _rule(_all(_contains("norte")), [NORTH], enabled=False, rule_id="r-0")
    first = _rule(_all(_contains("norte")), [CLOSED], rule_id="r-1")
    second = _rule(_all(_contains("norte")), [NORTH], rule_id="r-2")

    assert [found.rule_id for found in outcomes([off, first, second], "norte", "g-1")] == ["r-1", "r-2"]


def test_it_highlights_the_texts_it_looks_for_that_the_message_says():
    rule = _rule(
        _any(_contains("Norte", "puente"), _not_contains("sur"), _any(_contains("cerrado"))),
        [{"type": "highlight"}],
    )

    assert outcome([rule], "por el norte, cerrado", "g-1").highlights == ["Norte", "cerrado"]
    assert outcome([_rule(rule.conditions, [CLOSED])], "norte", "g-1").highlights == []


def test_a_suggestion_with_conditions_of_its_own_is_made_only_when_the_message_meets_them():
    # From the north group: the place when it is named, the status when it is said
    rule = _rule(
        _all(_group_is("g-north")),
        [{**NORTH, "conditions": _all(_contains("puente norte", "el puente"))},
         {**CLOSED, "conditions": _all(_contains("cerrado", "cortado"))},
         {"type": "highlight"}],
    )

    both = outcome([rule], "cortaron el puente, está cortado", "g-north")
    assert (both.point_id, both.value_id, both.highlights) == ("p-north", "v-closed", ["el puente", "cortado"])
    place = outcome([rule], "pasen por el puente", "g-north")
    assert (place.point_id, place.value_id, place.highlights) == ("p-north", None, ["el puente"])
    # A status alone is not about this place
    assert outcome([rule], "cerrado", "g-north") is None
    assert outcome([rule], "todo bien", "g-north") is None
    assert outcome([rule], "el puente, cerrado", "g-south") is None


def test_a_rule_about_a_place_says_nothing_of_a_message_that_does_not_name_it():
    # The status alone of a message about another place is not the status of this one
    bridge = _rule(_all(_group_is("g-north")), [
        {**NORTH, "conditions": _any(_contains("puente"))},
        {**CLOSED, "conditions": _any(_contains("cerrado", "cerrada"))},
    ], rule_id="r-bridge")
    clinic = _rule(_all(), [
        {"type": "suggest_place", "point_id": "p-clinic", "conditions": _any(_contains("salita"))},
        {**CLOSED, "conditions": _any(_contains("cerrada"))},
    ], rule_id="r-clinic")

    found = outcome([bridge, clinic], "la salita está cerrada", "g-north")
    # Only the rule about the place it names applies
    assert (found.rule_id, found.point_id, found.value_id) == ("r-clinic", "p-clinic", "v-closed")
    # Without a place of its own, a status is suggested alone
    status = _rule(_all(_group_is("g-north")), [{**CLOSED, "conditions": _any(_contains("cerrado"))}])
    assert (outcome([status], "cerrado", "g-north").point_id, outcome([status], "cerrado", "g-north").value_id) == (None, "v-closed")


def test_a_rule_can_have_conditions_only_in_its_actions_but_not_none_anywhere():
    names = _rule(_all(), [{**NORTH, "conditions": _any(_contains("norte"))}])
    nowhere = _rule(_all(), [NORTH])

    assert outcome([names], "por el norte", "g-1").point_id == "p-north"
    assert outcome([names], "por el sur", "g-1") is None
    assert outcome([nowhere], "por el norte", "g-1") is None


def test_a_rule_that_hides_says_so_and_none_matching_gives_none():
    rule = _rule(_all(_contains("hola a todos")), [{"type": "hide"}])

    assert outcome([rule], "Hola a todos!", "g-1").hide
    assert outcome([rule], "cerrado", "g-1") is None
    assert outcome([], "cerrado", "g-1") is None
