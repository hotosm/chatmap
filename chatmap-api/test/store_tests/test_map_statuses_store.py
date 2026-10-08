from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from db import Map, MapStatus, Point, SharePermission
from results.error import (
    ArchivedStatus,
    NotAuthorized,
    StatusInUse,
    StoreUnavailable,
    UnknownStatus,
)
from store.map_statuses_store import MapStatusesStore

GREEN = "#3E9E47"
RED = "#D73F3F"


def _patch_scope(*dbs):
    scope = MagicMock()
    scope.return_value.__enter__.side_effect = list(dbs)
    scope.return_value.__exit__.return_value = False
    return patch("store.map_statuses_store.session_scope", scope)


def _status(status_id="s-1", map_id="map-1", name="Open", color=GREEN, position=0, archived_at=None):
    return MapStatus(
        id=status_id, map_id=map_id, name=name, description="", color=color, position=position,
        archived_at=archived_at,
    )


def _db_statuses(*statuses):
    db = MagicMock()
    db.execute.return_value.scalars.return_value = list(statuses)
    return db


def _scalars(*rows):
    result = MagicMock()
    result.scalars.return_value = list(rows)
    return result


def _db_map(map_obj, existing=(), in_use=()):
    db = MagicMock()
    db.get.return_value = map_obj
    # The statuses of the map, the ones some point has among those left out, and their removal
    db.execute.side_effect = [_scalars(*existing), _scalars(*in_use), MagicMock()]
    return db


def _db_point(point, owner_id="user-1", status=None):
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = (
        None if point is None else SimpleNamespace(Point=point, owner_id=owner_id)
    )
    db.get.return_value = status
    return db


def _map(owner_id="user-1"):
    return Map(id="map-1", owner_id=owner_id)


def _point():
    return Point(id="p-1", map_id="map-1")


def _failing_db():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")
    db.get.side_effect = SQLAlchemyError("boom")
    return db


# ---- statuses_for ----

async def test_statuses_for_returns_the_statuses_of_the_map():
    statuses = [_status("s-1"), _status("s-2", name="Closed", color=RED, position=1)]

    with _patch_scope(_db_statuses(*statuses)):
        result = await MapStatusesStore.statuses_for("map-1")

    assert result == statuses


async def test_statuses_for_reports_the_store_as_unavailable():
    with _patch_scope(_failing_db()), pytest.raises(StoreUnavailable):
        await MapStatusesStore.statuses_for("map-1")


# ---- read_statuses ----

def _db_read(map_obj, statuses=(), points=()):
    db = MagicMock()
    db.get.return_value = map_obj
    db.execute.return_value.scalars.return_value = list(statuses)
    db.execute.return_value.all.return_value = list(points)
    return db


def _point_row(point_id="p-1", status_id="s-1"):
    return SimpleNamespace(id=point_id, status_id=status_id, status_updated_at=None)


async def test_read_returns_the_statuses_and_the_points_having_one():
    statuses = [_status("s-1")]
    points = [_point_row()]

    with _patch_scope(_db_read(_map(), statuses, points)):
        result = await MapStatusesStore.read_statuses("map-1", "user-1")

    assert result == (statuses, points)


async def test_read_only_takes_points_with_a_status_of_the_map():
    db = _db_read(_map(), [_status("s-1"), _status("s-2", name="Closed", position=1)])

    with _patch_scope(db):
        await MapStatusesStore.read_statuses("map-1", "user-1")

    query = db.execute.call_args_list[-1].args[0]
    assert ["s-1", "s-2"] in query.compile().params.values()


async def test_read_shows_removed_points_to_the_owner_only():
    owner_db = _db_read(_map(), [_status("s-1")])
    visitor_db = _db_read(Map(id="map-1", owner_id="user-1", sharing=SharePermission.PUBLIC), [_status("s-1")])

    with _patch_scope(owner_db):
        await MapStatusesStore.read_statuses("map-1", "user-1")
    with _patch_scope(visitor_db):
        await MapStatusesStore.read_statuses("map-1", None)

    assert "removed" not in str(owner_db.execute.call_args_list[-1].args[0])
    assert "removed" in str(visitor_db.execute.call_args_list[-1].args[0])


async def test_read_lets_anyone_see_a_public_map():
    public = Map(id="map-1", owner_id="someone-else", sharing=SharePermission.PUBLIC)

    with _patch_scope(_db_read(public, [_status("s-1")])):
        result = await MapStatusesStore.read_statuses("map-1", None)

    assert result is not None


@pytest.mark.parametrize("map_obj", [
    None,
    Map(id="map-1", owner_id="someone-else", sharing=SharePermission.PRIVATE),
])
async def test_read_does_not_find_a_map_the_user_cannot_see(map_obj):
    with _patch_scope(_db_read(map_obj)):
        assert await MapStatusesStore.read_statuses("map-1", "user-1") is None


async def test_read_reports_the_store_as_unavailable():
    with _patch_scope(_failing_db()), pytest.raises(StoreUnavailable):
        await MapStatusesStore.read_statuses("map-1", "user-1")


# ---- set_statuses ----

async def test_set_adds_the_statuses_in_the_given_order():
    db = _db_map(_map())

    with _patch_scope(db, _db_statuses()):
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": None, "name": "Open", "description": "", "color": GREEN},
            {"id": None, "name": "Closed", "description": "Nobody can pass", "color": RED},
        ])

    added = [call.args[0] for call in db.add.call_args_list]
    assert [(row.map_id, row.name, row.description, row.color, row.position) for row in added] == [
        ("map-1", "Open", "", GREEN, 0), ("map-1", "Closed", "Nobody can pass", RED, 1),
    ]
    db.commit.assert_called_once()


async def test_set_keeps_the_id_of_a_status_being_edited():
    existing = _status("s-1")
    db = _db_map(_map(), existing=[existing])

    with _patch_scope(db, _db_statuses(existing)):
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": "s-1", "name": "Abierto", "description": "", "color": RED},
        ])

    assert (existing.id, existing.name, existing.color) == ("s-1", "Abierto", RED)
    db.add.assert_not_called()
    # Only the read of the existing statuses: nothing to remove
    db.execute.assert_called_once()


async def test_set_removes_a_status_left_out():
    kept = _status("s-1")
    stale = _status("s-2", name="Closed", color=RED, position=1)
    db = _db_map(_map(), existing=[kept, stale])

    with _patch_scope(db, _db_statuses(kept)):
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": "s-1", "name": "Open", "description": "", "color": GREEN},
        ])

    removal = db.execute.call_args_list[-1].args[0]
    assert removal.is_delete
    assert removal.compile().params == {"id_1": ["s-2"]}
    db.commit.assert_called_once()


async def test_set_does_not_remove_a_status_some_points_have():
    kept = _status("s-1")
    stale = _status("s-2", name="Closed", color=RED, position=1)
    db = _db_map(_map(), existing=[kept, stale], in_use=["s-2"])

    with _patch_scope(db), pytest.raises(StatusInUse) as raised:
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": "s-1", "name": "Open", "description": "", "color": GREEN},
        ])

    assert raised.value.status_ids == ["s-2"]
    assert not any(call.args[0].is_delete for call in db.execute.call_args_list)
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


async def test_set_archives_and_restores_a_status():
    existing = _status("s-1")
    db = _db_map(_map(), existing=[existing])

    with _patch_scope(db, _db_statuses(existing)):
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": "s-1", "name": "Open", "description": "", "color": GREEN, "archived": True},
        ])

    assert existing.archived_at.tzinfo is not None

    db = _db_map(_map(), existing=[existing])

    with _patch_scope(db, _db_statuses(existing)):
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": "s-1", "name": "Open", "description": "", "color": GREEN},
        ])

    assert existing.archived_at is None


async def test_set_keeps_the_date_of_a_status_already_archived():
    archived_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    existing = _status("s-1", archived_at=archived_at)
    db = _db_map(_map(), existing=[existing])

    with _patch_scope(db, _db_statuses(existing)):
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": "s-1", "name": "Abierto", "description": "", "color": GREEN, "archived": True},
        ])

    assert (existing.name, existing.archived_at) == ("Abierto", archived_at)


async def test_set_takes_an_id_from_another_map_as_a_new_status():
    db = _db_map(_map())

    with _patch_scope(db, _db_statuses()):
        await MapStatusesStore.set_statuses("map-1", "user-1", [
            {"id": "s-9", "name": "Open", "description": "", "color": GREEN},
        ])

    added = db.add.call_args.args[0]
    assert added.id != "s-9"
    assert added.map_id == "map-1"


@pytest.mark.parametrize("map_obj", [None, Map(id="map-1", owner_id="someone-else")])
async def test_set_rejects_a_map_the_user_does_not_own(map_obj):
    db = _db_map(map_obj)

    with _patch_scope(db), pytest.raises(NotAuthorized):
        await MapStatusesStore.set_statuses("map-1", "user-1", [])

    db.commit.assert_not_called()


async def test_set_reports_the_store_as_unavailable():
    db = _failing_db()

    with _patch_scope(db), pytest.raises(StoreUnavailable):
        await MapStatusesStore.set_statuses("map-1", "user-1", [])

    db.rollback.assert_called_once()


# ---- set_point_status ----

async def test_set_point_status_saves_the_status_with_its_date():
    point = _point()
    db = _db_point(point, status=_status("s-1"))

    with _patch_scope(db):
        status_id, updated_at = await MapStatusesStore.set_point_status("p-1", "user-1", "s-1")

    assert status_id == "s-1"
    assert updated_at.tzinfo is not None
    assert (point.status_id, point.status_updated_at) == ("s-1", updated_at)
    db.commit.assert_called_once()


async def test_set_point_status_can_leave_the_point_without_status():
    point = _point()
    point.status_id = "s-1"
    db = _db_point(point)

    with _patch_scope(db):
        result = await MapStatusesStore.set_point_status("p-1", "user-1", None)

    assert result == (None, None)
    assert (point.status_id, point.status_updated_at) == (None, None)


@pytest.mark.parametrize("status", [None, MapStatus(id="s-1", map_id="map-2")])
async def test_set_point_status_rejects_a_status_that_is_not_of_the_map(status):
    point = _point()
    db = _db_point(point, status=status)

    with _patch_scope(db), pytest.raises(UnknownStatus):
        await MapStatusesStore.set_point_status("p-1", "user-1", "s-1")

    assert point.status_id is None
    db.commit.assert_not_called()


async def test_set_point_status_rejects_an_archived_status():
    point = _point()
    db = _db_point(point, status=_status("s-1", archived_at=datetime(2026, 10, 1, tzinfo=UTC)))

    with _patch_scope(db), pytest.raises(ArchivedStatus):
        await MapStatusesStore.set_point_status("p-1", "user-1", "s-1")

    assert point.status_id is None
    db.commit.assert_not_called()


async def test_set_point_status_rejects_a_point_that_does_not_exist():
    with _patch_scope(_db_point(None)), pytest.raises(NotAuthorized):
        await MapStatusesStore.set_point_status("p-1", "user-1", "s-1")


async def test_set_point_status_rejects_a_user_who_does_not_own_the_map():
    point = _point()
    db = _db_point(point, owner_id="someone-else", status=_status("s-1"))

    with _patch_scope(db), pytest.raises(NotAuthorized):
        await MapStatusesStore.set_point_status("p-1", "user-1", "s-1")

    assert point.status_id is None
    db.commit.assert_not_called()


async def test_set_point_status_reports_the_store_as_unavailable():
    db = _failing_db()

    with _patch_scope(db), pytest.raises(StoreUnavailable):
        await MapStatusesStore.set_point_status("p-1", "user-1", "s-1")

    db.rollback.assert_called_once()
