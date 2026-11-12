from unittest.mock import MagicMock, patch

import pytest

from db import Map, MapKey, MapKeyValue, MessageRule, Point
from results.error import (
    ArchivedValue,
    InvalidRule,
    MapNotFound,
    TooManyRules,
    UnknownGroup,
    UnknownKey,
    UnknownPoint,
    UnknownRule,
)
from store.message_rules_store import MessageRulesStore


def _all(*items):
    return {"match": "all", "items": list(items)}


def _contains(*values):
    return {"field": "content", "operator": "contains", "values": list(values)}


def _group_is(*values):
    return {"field": "group", "operator": "is", "values": list(values)}


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.message_rules_store.session_scope", scope)


def _fields(conditions=None, actions=None):
    return {
        "description": "North access", "enabled": True,
        "conditions": {"match": "all", "items": conditions or [_contains("norte")]},
        "actions": actions or [{"type": "highlight", "point_id": None, "key_id": None, "value_id": None}],
    }


def _db(map_obj=Map(id="map-1", owner_id="user-1"), count=0, found=None):
    """A session with the map locked, how many rules it has, and what db.get finds by model."""
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = map_obj
    db.execute.return_value.scalar_one.return_value = count
    db.execute.return_value.scalars.return_value = ["g-1"]
    found = found or {}
    db.get.side_effect = lambda model, row_id: found.get((model, row_id), map_obj if model is Map else None)
    return db


@pytest.mark.parametrize("call", [
    lambda: MessageRulesStore.create_rule("map-1", "user-1", _fields(), 50),
    lambda: MessageRulesStore.rules("map-1", "user-1"),
    lambda: MessageRulesStore.update_rule("map-1", "r-1", "user-1", _fields()),
    lambda: MessageRulesStore.remove_rule("map-1", "r-1", "user-1"),
])
async def test_only_the_owner_reads_and_writes_the_rules_of_a_map(call):
    db = _db(map_obj=Map(id="map-1", owner_id="user-2"))
    with _patch_scope(db), pytest.raises(MapNotFound):
        await call()
    db.commit.assert_not_called()


async def test_a_map_takes_up_to_a_number_of_rules():
    with _patch_scope(_db(count=50)), pytest.raises(TooManyRules):
        await MessageRulesStore.create_rule("map-1", "user-1", _fields(), 50)


async def test_a_new_rule_keeps_only_what_its_actions_need():
    db = _db(count=2)

    with _patch_scope(db):
        row = await MessageRulesStore.create_rule("map-1", "user-1", _fields(), 50)

    assert row.actions == [{"type": "highlight"}]
    db.commit.assert_called_once()


async def test_a_rule_names_groups_of_its_map_inside_its_groups_too():
    inner = {"match": "any", "items": [_group_is("g-1", "g-9")]}

    with _patch_scope(_db()), pytest.raises(UnknownGroup):
        await MessageRulesStore.create_rule("map-1", "user-1", _fields([_contains("a"), inner]), 50)


async def test_a_rule_names_groups_of_its_map_in_the_conditions_of_its_actions_too():
    action = {"type": "suggest_place", "point_id": "p-1", "conditions": _all(_group_is("g-9"))}

    with _patch_scope(_db(found={(Point, "p-1"): Point(id="p-1", map_id="map-1")})), pytest.raises(UnknownGroup):
        await MessageRulesStore.create_rule("map-1", "user-1", _fields(actions=[action]), 50)


@pytest.mark.parametrize("point", [
    None, Point(id="p-1", map_id="map-2", place=True), Point(id="p-1", map_id="map-1", removed=True, place=True),
    # A report of a message, not a place
    Point(id="p-1", map_id="map-1", removed=False, place=False),
])
async def test_a_rule_suggests_a_place_of_its_map_not_removed(point):
    action = {"type": "suggest_place", "point_id": "p-1", "key_id": None, "value_id": None}

    with _patch_scope(_db(found={(Point, "p-1"): point})), pytest.raises(UnknownPoint):
        await MessageRulesStore.create_rule("map-1", "user-1", _fields(actions=[action]), 50)


@pytest.mark.parametrize("key, value, error", [
    (MapKey(id="k-1", map_id="map-2", closed=True), None, UnknownKey),
    (MapKey(id="k-1", map_id="map-1", closed=False), None, InvalidRule),
    (MapKey(id="k-1", map_id="map-1", closed=True), MapKeyValue(id="v-1", key_id="k-1", archived_at="2026-10-01"), ArchivedValue),
])
async def test_a_rule_suggests_a_value_not_archived_of_a_key_with_a_list_of_its_map(key, value, error):
    action = {"type": "suggest_status", "point_id": None, "key_id": "k-1", "value_id": "v-1"}

    with _patch_scope(_db(found={(MapKey, "k-1"): key, (MapKeyValue, "v-1"): value})), pytest.raises(error):
        await MessageRulesStore.create_rule("map-1", "user-1", _fields(actions=[action]), 50)


async def test_a_rule_of_another_map_is_not_found():
    db = _db(found={(MessageRule, "r-1"): MessageRule(id="r-1", map_id="map-2")})

    with _patch_scope(db), pytest.raises(UnknownRule):
        await MessageRulesStore.update_rule("map-1", "r-1", "user-1", _fields())
    with _patch_scope(db), pytest.raises(UnknownRule):
        await MessageRulesStore.remove_rule("map-1", "r-1", "user-1")
