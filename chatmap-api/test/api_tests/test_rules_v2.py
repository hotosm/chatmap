from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.v2.routes.rules import create_rule
from api.v2.schemas.rules import RuleAction, RuleCondition, RuleFields
from results.error import MapNotFound, TooManyRules, UnknownPoint


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.rules.MessageRulesStore.{method}", AsyncMock(**kwargs))


def _contains(*values, operator="contains"):
    return {"field": "content", "operator": operator, "values": list(values)}


def _fields(items=None, **changes):
    rule = {
        "description": " North access ",
        "conditions": {"match": "all", "items": items or [_contains(" norte ")]},
        "actions": [{"type": "suggest_place", "point_id": "p-1"}],
    }
    return RuleFields(**{**rule, **changes})


# ---- what a rule may be ----

def test_a_rule_is_trimmed_and_needs_conditions_and_actions():
    rule = _fields()
    assert (rule.description, rule.conditions.items[0].values, rule.enabled) == ("North access", ["norte"], True)
    for changes in ({"conditions": {"match": "all", "items": []}}, {"actions": []}, {"description": "  "}):
        with pytest.raises(ValidationError):
            _fields(**changes)


def test_the_conditions_of_a_rule_can_be_in_its_suggestions_only():
    place = {"type": "suggest_place", "point_id": "p-1", "conditions": {"match": "any", "items": [_contains("puente")]}}
    rule = RuleFields(description="North bridge", actions=[place, {"type": "highlight"}])

    assert (rule.conditions.items, rule.actions[0].conditions.items[0].values) == ([], ["puente"])
    assert rule.model_dump()["actions"][1]["conditions"] is None


def test_only_suggestions_take_conditions_and_these_are_not_empty_nor_hold_groups():
    inner = {"match": "any", "items": [_contains("cerrado")]}
    for action in (
        {"type": "hide", "conditions": {"match": "all", "items": [_contains("hola")]}},
        {"type": "suggest_place", "point_id": "p-1", "conditions": {"match": "all", "items": []}},
        {"type": "suggest_place", "point_id": "p-1", "conditions": {"match": "all", "items": [inner]}},
    ):
        with pytest.raises(ValidationError):
            RuleAction(**action)
    with pytest.raises(ValidationError):
        _fields([{"match": "any", "items": []}])


def test_a_condition_takes_values_once_and_an_operator_of_its_field():
    assert _fields([_contains("cerrado", " cerrado", "cerrada")]).conditions.items[0].values == ["cerrado", "cerrada"]
    for condition in (
        _contains(),
        _contains("x" * 101),
        _contains("norte", operator="is"),
        {"field": "group", "operator": "contains", "values": ["g-1"]},
    ):
        with pytest.raises(ValidationError):
            _fields([condition])


def test_groups_of_conditions_go_one_level_down_and_a_rule_has_a_limit():
    inner = {"match": "any", "items": [_contains("cerrado"), _contains("bloqueado")]}
    assert _fields([inner, _contains("norte")]).conditions.items[0].match == "any"
    with pytest.raises(ValidationError):
        _fields([{"match": "any", "items": [inner]}])
    with pytest.raises(ValidationError):
        _fields([{"match": "any", "items": [_contains(str(i)) for i in range(10)]} for _ in range(3)])


def test_each_action_takes_what_it_needs_and_nothing_else():
    assert RuleAction(type="suggest_status", key_id="k-1", value_id="v-1").value_id == "v-1"
    for action in (
        {"type": "suggest_place"},
        {"type": "suggest_status", "key_id": "k-1"},
        {"type": "highlight", "point_id": "p-1"},
        {"type": "hide", "value_id": "v-1"},
    ):
        with pytest.raises(ValidationError):
            RuleAction(**action)


def test_a_rule_that_hides_does_nothing_else_and_highlighting_needs_a_text_it_contains():
    with pytest.raises(ValidationError):
        _fields(actions=[{"type": "hide"}, {"type": "highlight"}])
    with pytest.raises(ValidationError):
        _fields(actions=[{"type": "highlight"}, {"type": "highlight"}])
    with pytest.raises(ValidationError):
        _fields([_contains("sur", operator="not_contains")], actions=[{"type": "highlight"}])
    # The text it contains can be one an action looks for
    place = {"type": "suggest_place", "point_id": "p-1", "conditions": {"match": "all", "items": [_contains("puente")]}}
    assert _fields([_contains("sur", operator="not_contains")], actions=[place, {"type": "highlight"}])
    group = {"field": "group", "operator": "is", "values": ["g-1"]}
    assert _fields([group], actions=[{"type": "hide"}]).actions[0].type == "hide"


# ---- routes ----


@pytest.mark.parametrize("error, status_code", [(MapNotFound(), 404), (UnknownPoint("p-1"), 404), (TooManyRules(50), 409)])
async def test_creating_a_rule_tells_what_failed(error, status_code):
    with _patch_store("create_rule", side_effect=error), pytest.raises(HTTPException) as raised:
        await create_rule(map_id="map-1", rule=_fields(), user=_user())

    assert raised.value.status_code == status_code


@pytest.mark.parametrize("condition", [
    # Without the zone it was written in
    {"field": "time", "operator": "between", "values": ["08:00", "12:00"]},
    {"field": "time", "operator": "between", "values": ["08:00", "12:00"], "timezone": "Mars/Olympus"},
    # One time, the same twice, or not a time of the day
    {"field": "time", "operator": "between", "values": ["08:00"], "timezone": "UTC"},
    {"field": "time", "operator": "between", "values": ["08:00", "08:00"], "timezone": "UTC"},
    {"field": "time", "operator": "between", "values": ["8", "25:00"], "timezone": "UTC"},
    {"field": "weekday", "operator": "is", "values": ["monday"], "timezone": "UTC"},
    {"field": "weekday", "operator": "is_not", "values": ["mon"], "timezone": "UTC"},
    {"field": "content", "operator": "contains", "values": ["norte"], "timezone": "UTC"},
])
def test_a_condition_on_when_a_message_was_sent_takes_valid_times_days_and_zone(condition):
    with pytest.raises(ValidationError):
        RuleCondition(**condition)
