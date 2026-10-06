from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from db import Map, SharePermission
from results.error import StoreUnavailable
from store.maps_store import MapsStore


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.maps_store.session_scope", scope)


def _db(map_obj, points=()):
    db = MagicMock()
    db.get.return_value = map_obj
    db.execute.return_value.all.return_value = list(points)
    return db


def _map(sharing=SharePermission.PRIVATE, owner_id="user-1"):
    return Map(id="map-1", sharing=sharing, owner_id=owner_id)


# ---- read_map ----

async def test_read_returns_the_map_and_its_points_to_the_owner():
    map_obj = _map()

    with _patch_scope(_db(map_obj, points=["a point"])):
        result = await MapsStore.read_map("map-1", "user-1")

    assert result == (map_obj, True, ["a point"])


async def test_read_lets_anyone_see_a_public_map():
    map_obj = _map(sharing=SharePermission.PUBLIC)

    with _patch_scope(_db(map_obj)):
        result = await MapsStore.read_map("map-1", None)

    assert result == (map_obj, False, [])


@pytest.mark.parametrize("map_obj", [None, Map(id="map-1", sharing=SharePermission.PRIVATE, owner_id="someone-else")])
async def test_read_does_not_find_a_map_the_user_cannot_see(map_obj):
    db = _db(map_obj)

    with _patch_scope(db):
        assert await MapsStore.read_map("map-1", "user-1") is None

    db.execute.assert_not_called()


async def test_read_shows_removed_points_to_the_owner_only():
    owner_db = _db(_map())
    visitor_db = _db(_map(sharing=SharePermission.PUBLIC))

    with _patch_scope(owner_db):
        await MapsStore.read_map("map-1", "user-1")
    with _patch_scope(visitor_db):
        await MapsStore.read_map("map-1", None)

    assert "removed = false" not in str(owner_db.execute.call_args.args[0])
    assert "removed = false" in str(visitor_db.execute.call_args.args[0])


async def test_read_reports_the_store_as_unavailable():
    db = _db(_map())
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await MapsStore.read_map("map-1", "user-1")
