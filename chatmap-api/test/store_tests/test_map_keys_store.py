from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from db import Map, MapKey, MapKeyValue
from results.error import InvalidTagValue, KeyInUse, KeyNameTaken, NotAuthorized, TooManyKeys, UnknownKey, ValueInUse
from store.map_keys_store import MapKeysStore, save_values


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.map_keys_store.session_scope", scope)


def _map(owner_id="user-1"):
    return Map(id="map-1", owner_id=owner_id)


def _result(first=None, scalar=None, scalars=()):
    result = MagicMock()
    result.first.return_value = first
    result.scalar.return_value = scalar
    result.scalars.return_value = list(scalars)
    return result


def _fuel(**fields):
    return {"key": "Fuel", "single": True, "closed": True, "values": [], **fields}


# ---- create_key ----

async def test_only_the_owner_creates_keys():
    db = MagicMock()
    db.get.return_value = _map(owner_id="someone-else")

    with _patch_scope(db), pytest.raises(NotAuthorized):
        await MapKeysStore.create_key("map-1", "user-1", _fuel(), 10)


async def test_a_key_name_is_once_per_map():
    db = MagicMock()
    db.get.return_value = _map()
    db.execute.return_value = _result(first=("k-1",))

    with _patch_scope(db), pytest.raises(KeyNameTaken):
        await MapKeysStore.create_key("map-1", "user-1", _fuel(), 10)


async def test_a_map_takes_a_limited_number_of_keys():
    db = MagicMock()
    db.get.return_value = _map()
    # The name is free; the map already has as many keys as it can take
    db.execute.side_effect = [_result(first=None), _result(scalar=10)]

    with _patch_scope(db), pytest.raises(TooManyKeys):
        await MapKeysStore.create_key("map-1", "user-1", _fuel(), 10)


async def test_a_free_key_has_no_values():
    db = MagicMock()
    db.get.return_value = _map()
    db.execute.side_effect = [_result(first=None), _result(scalar=0)]

    with _patch_scope(db), pytest.raises(InvalidTagValue):
        await MapKeysStore.create_key("map-1", "user-1", _fuel(closed=False, values=[{"value": "x"}]), 10)


# ---- update_key, remove_key ----

async def test_a_key_of_another_map_is_not_found():
    db = MagicMock()
    db.get.side_effect = [_map(), MapKey(id="k-1", map_id="map-2")]

    with _patch_scope(db), pytest.raises(UnknownKey):
        await MapKeysStore.update_key("map-1", "k-1", "user-1", {"key": "Other"})


async def test_a_key_that_was_used_is_not_removed():
    db = MagicMock()
    db.get.side_effect = [_map(), MapKey(id="k-1", map_id="map-1")]
    db.execute.return_value = _result(first=(1,))

    with _patch_scope(db), pytest.raises(KeyInUse):
        await MapKeysStore.remove_key("map-1", "k-1", "user-1")

    db.delete.assert_not_called()


# ---- save_values ----

def test_saving_values_keeps_their_ids_and_adds_the_new_ones():
    open_value = MapKeyValue(id="v-1", key_id="k-1", value="Open", position=0)
    db = MagicMock()
    db.execute.return_value = _result(scalars=[open_value])

    save_values(db, MapKey(id="k-1"), [
        {"id": "v-1", "value": "Open now", "expires_after": 4},
        {"value": "Closed"},
    ])

    assert (open_value.value, open_value.expires_after, open_value.position) == ("Open now", timedelta(hours=4), 0)
    [new] = [call.args[0] for call in db.add.call_args_list]
    assert (new.value, new.expires_after, new.position) == ("Closed", None, 1)


def test_a_value_some_point_has_is_not_removed():
    db = MagicMock()
    db.execute.side_effect = [_result(scalars=[MapKeyValue(id="v-1", key_id="k-1")]), _result(first=(1,))]

    with pytest.raises(ValueInUse) as raised:
        save_values(db, MapKey(id="k-1"), [])

    assert raised.value.value_ids == ["v-1"]
