from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from db import MessageRule, MessageSuggestion
from store.suggestions import ROW_DEFAULTS, answer_on_link, suggest


def _scalars(*items):
    result = MagicMock()
    result.scalars.return_value = list(items)
    return result


def _rows_result(*rows):
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def _values(*values):
    """The values of the map with words: (id, key_id, words)."""
    return _rows_result(*(SimpleNamespace(id=v[0], key_id=v[1], words=v[2]) for v in values))


def _points(*points):
    """The places of the map with a name: (id, name)."""
    return _rows_result(*(SimpleNamespace(id=p[0], message=p[1]) for p in points))


def _rule(conditions, actions, rule_id="r-1", description="North closed"):
    return MessageRule(
        id=rule_id, map_id="map-1", description=description, enabled=True,
        conditions={"match": "all", "items": conditions}, actions=actions,
    )


def _contains(*values):
    return {"field": "content", "operator": "contains", "values": list(values)}


def _messages(*texts, hidden=()):
    rows = [{"id": f"m-{i}", "group_id": "group-1", "text": text, **ROW_DEFAULTS} for i, text in enumerate(texts)]
    for i in hidden:
        rows[i]["dismissed_by_rule"] = True
    return rows


def _db(*results):
    db = MagicMock()
    db.execute.side_effect = list(results)
    return db


def _said(found, message="m-0"):
    return [(s["line"], s["point_id"], s["value_id"], s["rule_id"], s["doubt"]) for s in found.get(message, [])]


NORTH = {"type": "suggest_place", "point_id": "p-north"}
CLOSED = {"type": "suggest_status", "key_id": "k-1", "value_id": "v-closed"}
OPEN = {"type": "suggest_status", "key_id": "k-1", "value_id": "v-open"}


# ---- the words of the map ----

def _words_db(points=(), names=(), group_places=()):
    """A map without rules, whose Closed and Open have words."""
    return _db(
        _scalars(),
        _values(("v-open", "k-1", ["abierto"]), ("v-closed", "k-1", ["cerrado", "🔴"])),
        _points(*points), _rows_result(*names), _rows_result(*group_places),
    )


def test_each_line_of_a_message_suggests_the_place_it_names_and_the_value_it_says():
    db = _words_db(points=[("p-north", "Acceso Norte"), ("p-bridge", "Puente")])

    found = suggest(db, "map-1", _messages("Así están:\nAcceso Norte abierto\nPuente 🔴", "hola"), {})

    assert _said(found) == [(1, "p-north", "v-open", None, None), (2, "p-bridge", "v-closed", None, None)]
    assert [s["words"] for s in found["m-0"]] == [["Acceso Norte", "abierto"], ["Puente", "🔴"]]
    assert all(s["message_id"] == "m-0" and s["state"] == "pending" for s in found["m-0"])
    assert "m-1" not in found


def test_a_place_is_named_by_its_other_names_too():
    db = _words_db(points=[("p-bridge", "Puente Viejo")], names=[("p-bridge", "el puente"), ("p-bridge", "الجسر")])

    found = suggest(db, "map-1", _messages("el puente cerrado\nالجسر cerrado"), {})

    assert [(s["line"], s["point_id"], s["words"][0]) for s in found["m-0"]] == [(0, "p-bridge", "el puente"), (1, "p-bridge", "الجسر")]


def test_a_line_without_a_place_speaks_of_the_place_of_its_group_and_a_hidden_message_suggests_nothing():
    db = _words_db(points=[("p-bridge", "Puente")], group_places=[("group-1", "p-bridge")])

    found = suggest(db, "map-1", _messages("cerrado", "Puente cerrado", hidden=(1,)), {})

    assert _said(found) == [(0, "p-bridge", "v-closed", None, None)]
    assert "m-1" not in found


# ---- the rules of the map ----

def _rules_db(rules, points=("p-north",), values=("v-closed", "v-open"), group_places=()):
    """
    A map with rules and without words: the places and values the rules name
    that it still has (each asked only when some rule names one).
    """
    actions = [action for rule in rules for action in rule.actions]
    still = [_scalars(*points)] if any("point_id" in action for action in actions) else []
    still += [_scalars(*values)] if any("value_id" in action for action in actions) else []
    return _db(_scalars(*rules), _values(), *still, _rows_result(*group_places))


def test_every_rule_a_message_meets_suggests_for_the_whole_message_and_what_they_look_for_is_highlighted():
    rules = [
        _rule([_contains("norte")], [{"type": "highlight"}, NORTH], rule_id="r-place"),
        _rule([_contains("cerrado")], [{"type": "highlight"}, CLOSED], rule_id="r-status"),
    ]
    rows = _messages("norte cerrado")

    found = suggest(_rules_db(rules), "map-1", rows, {"m-0": "g-1"})

    assert _said(found) == [(None, "p-north", None, "r-place", None), (None, None, "v-closed", "r-status", None)]
    assert found["m-0"][0]["rule"] == "North closed"
    assert rows[0]["highlights"] == ["norte", "cerrado"]


def test_a_value_without_a_place_goes_to_the_place_of_the_group_when_it_has_only_one():
    rules = [_rule([_contains("cerrado")], [CLOSED])]

    found = suggest(_rules_db(rules, group_places=[("group-1", "p-north")]), "map-1", _messages("cerrado"), {"m-0": "g-1"})

    assert _said(found) == [(None, "p-north", "v-closed", "r-1", None)]


def test_two_rules_giving_a_place_different_values_are_doubtful_and_a_question_too():
    rules = [
        _rule([_contains("norte")], [NORTH, CLOSED], rule_id="r-closed"),
        _rule([_contains("norte")], [NORTH, OPEN], rule_id="r-open"),
    ]

    found = suggest(_rules_db(rules), "map-1", _messages("norte"), {"m-0": "g-1"})
    assert [s["doubt"] for s in found["m-0"]] == ["two_values", "two_values"]

    asks = suggest(_rules_db(rules[:1]), "map-1", _messages("¿norte?"), {"m-0": "g-1"})
    assert [s["doubt"] for s in asks["m-0"]] == ["question"]


def test_a_rule_does_not_suggest_a_place_removed_since_nor_an_archived_value():
    rules = [_rule([_contains("cerrado")], [{"type": "highlight"}, NORTH, CLOSED])]
    rows = _messages("cerrado el norte")

    found = suggest(_rules_db(rules, points=(), values=()), "map-1", rows, {"m-0": "g-1"})

    # It still highlights what matched, but has nothing to suggest
    assert (found, rows[0]["highlights"]) == ({}, ["cerrado"])


def test_a_rule_that_hides_dismisses_the_message_and_it_suggests_nothing():
    rules = [_rule([_contains("hola a todos")], [{"type": "hide"}]), _rule([_contains("hola")], [NORTH])]
    rows = _messages("Hola a todos!")

    found = suggest(_rules_db(rules), "map-1", rows, {"m-0": "g-1"})

    assert found == {}
    assert rows[0]["dismissed_at"] is not None and rows[0]["dismissed_by_rule"]


def test_what_a_line_already_suggests_for_a_place_a_rule_does_not_say_again():
    rules = [_rule([_contains("norte")], [NORTH, CLOSED])]
    db = _db(
        _scalars(*rules), _values(("v-closed", "k-1", ["cerrado"])), _points(("p-north", "norte")), _rows_result(),
        _scalars("p-north"), _scalars("v-closed"), _rows_result(),
    )

    found = suggest(db, "map-1", _messages("norte cerrado"), {"m-0": "g-1"})

    assert _said(found) == [(0, "p-north", "v-closed", None, None)]


# ---- a link answers what a message suggests ----

def _pending(point_id="p-1", key_id="k-1", value_id="v-1", rule_id="r-1"):
    return MessageSuggestion(
        id="s-1", message_id="m-1", point_id=point_id, key_id=key_id, value_id=value_id, rule_id=rule_id, state="pending",
    )


@pytest.mark.parametrize("suggestion, state, by_rule", [
    (_pending(), "accepted", True),
    # What the words of the map suggested: confirmed, but the change is the message's
    (_pending(rule_id=None), "accepted", False),
    # Another value for its place and key: it was wrong
    (_pending(value_id="v-2"), "rejected", False),
    # Only the place: any link to it confirms it
    (_pending(key_id=None, value_id=None), "accepted", True),
    # Only the value: a link of it confirms it, wherever it goes
    (_pending(point_id=None), "accepted", True),
])
def test_a_link_confirms_what_gives_what_it_gives_and_what_gives_another_value_was_wrong(suggestion, state, by_rule):
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [suggestion]

    assert answer_on_link(db, "m-1", "p-1", "k-1", "v-1") is by_rule
    assert suggestion.state == state
