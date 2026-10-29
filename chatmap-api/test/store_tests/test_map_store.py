from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from results.error import MapNotFound, NotAuthorized, StoreUnavailable
from store.contributors.authorization import Owner
from store.credentials import Credentials
from store.maps.store import MapStore, OwnedMap

_SECRET = "s" * 43


def _rows(*rows):
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def _scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _db(*results):
    db = MagicMock()
    db.execute.side_effect = list(results)
    return db


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.maps.store.session_scope", scope)


def _maps_query(db):
    return db.execute.call_args.args[0].compile(dialect=postgresql.dialect())


async def test_owned_by_returns_each_map_in_the_order_the_query_gives():
    db = _db(_rows(("map-1", "Mapa uno"), ("map-2", None)))

    with _patch_scope(db):
        maps = await MapStore.owned_by("user-1")

    assert maps == [
        OwnedMap(map_id="map-1", map_name="Mapa uno"),
        OwnedMap(map_id="map-2", map_name=None),
    ]


async def test_owned_by_is_empty_when_the_user_owns_no_maps():
    db = _db(_rows())

    with _patch_scope(db):
        maps = await MapStore.owned_by("user-1")

    assert maps == []


async def test_owned_by_filters_by_the_owner():
    db = _db(_rows())

    with _patch_scope(db):
        await MapStore.owned_by("user-1")

    query = _maps_query(db)
    assert "WHERE maps.owner_id = " in str(query)
    assert "user-1" in query.params.values()


async def test_owned_by_orders_from_the_oldest_map_to_the_newest():
    db = _db(_rows())

    with _patch_scope(db):
        await MapStore.owned_by("user-1")

    assert "ORDER BY maps.created_at, maps.id" in str(_maps_query(db))


async def test_owned_by_reports_the_store_unavailable_when_the_query_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await MapStore.owned_by("user-1")


# ---- role_of ----

async def test_role_of_rejects_a_map_that_does_not_exist():
    db = _db(_scalar(None))

    with _patch_scope(db):
        with pytest.raises(MapNotFound):
            await MapStore.role_of("map-1", Credentials(contributor_secret=_SECRET))

    assert db.execute.call_count == 1


async def test_role_of_the_owner_is_the_owner():
    with _patch_scope(_db(_scalar("user-1"))):
        role = await MapStore.role_of("map-1", Credentials(user_id="user-1", username="joaco"))

    assert role == Owner(user_id="user-1", username="joaco")


async def test_role_of_a_session_of_another_user_hides_the_map():
    with _patch_scope(_db(_scalar("someone-else"))):
        with pytest.raises(MapNotFound):
            await MapStore.role_of("map-1", Credentials(user_id="user-1"))


async def test_role_of_an_active_contributor_is_that_contributor():
    contributor = SimpleNamespace(id="c-1", removed_at=None)

    with _patch_scope(_db(_scalar("owner-1"), _scalar(contributor))):
        role = await MapStore.role_of("map-1", Credentials(contributor_secret=_SECRET))

    assert role is contributor


async def test_role_of_a_secret_that_is_not_a_contributor_is_not_authorized():
    with _patch_scope(_db(_scalar("owner-1"), _scalar(None))):
        with pytest.raises(NotAuthorized):
            await MapStore.role_of("map-1", Credentials(contributor_secret=_SECRET))


async def test_role_of_reports_the_store_unavailable_when_the_lookup_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await MapStore.role_of("map-1", Credentials(user_id="user-1"))
