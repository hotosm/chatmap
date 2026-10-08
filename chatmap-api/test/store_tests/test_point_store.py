from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from results.error import MapNotFound, PointIdAlreadyTaken, StoreUnavailable
from store.point_store import PointStore

_TIME = datetime(2026, 10, 7, 12, 15, 23, tzinfo=timezone(timedelta(hours=-3)))


def _result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar_one.return_value = value
    return result


def _db(*values):
    db = MagicMock()
    db.execute.side_effect = [_result(value) for value in values]
    return db


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.point_store.session_scope", scope)


async def _create(map_id="map-1", user_id="user-1"):
    return await PointStore.create_point(
        point_id="p-1",
        map_id=map_id,
        user_id=user_id,
        username="joaco",
        latitude=-34.6,
        longitude=-58.38,
        time=_TIME,
        message="Calle inundada",
    )


def _insert_params(db):
    query = db.execute.call_args_list[1].args[0]
    return query.compile(dialect=postgresql.dialect()).params


async def test_create_rejects_a_map_that_does_not_exist():
    db = _db(None)

    with _patch_scope(db):
        with pytest.raises(MapNotFound):
            await _create()

    assert db.execute.call_count == 1
    db.commit.assert_not_called()


async def test_create_rejects_a_map_of_another_user():
    db = _db("someone-else")

    with _patch_scope(db):
        with pytest.raises(MapNotFound):
            await _create()

    assert db.execute.call_count == 1
    db.commit.assert_not_called()


async def test_create_saves_a_new_point():
    db = _db("user-1", "p-1")

    with _patch_scope(db):
        created = await _create()

    assert created is True
    db.commit.assert_called_once()


async def test_create_maps_the_fields_to_the_point_columns():
    db = _db("user-1", "p-1")

    with _patch_scope(db):
        await _create()

    params = _insert_params(db)
    assert params["id"] == "p-1"
    assert params["map_id"] == "map-1"
    assert params["geom"] == "POINT(-58.38 -34.6)"
    assert params["message"] == "Calle inundada"
    assert params["username"] == "joaco"


async def test_create_stores_the_time_in_utc_without_timezone():
    db = _db("user-1", "p-1")

    with _patch_scope(db):
        await _create()

    assert _insert_params(db)["time"] == datetime(2026, 10, 7, 15, 15, 23)


async def test_create_does_not_modify_a_point_that_already_exists_in_the_map():
    db = _db("user-1", None, "map-1")

    with _patch_scope(db):
        created = await _create()

    assert created is False
    assert db.execute.call_count == 3


async def test_create_rejects_an_id_used_in_another_map():
    db = _db("user-1", None, "map-2")

    with _patch_scope(db):
        with pytest.raises(PointIdAlreadyTaken):
            await _create()


async def test_create_reports_the_store_unavailable_when_the_map_lookup_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _create()

    db.commit.assert_not_called()


async def test_create_rolls_back_when_saving_fails():
    db = MagicMock()
    db.execute.side_effect = [_result("user-1"), SQLAlchemyError("boom")]

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _create()

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
