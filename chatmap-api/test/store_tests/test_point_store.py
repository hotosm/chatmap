import base64
import json
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from results.error import InvalidCursor, StoreUnavailable
from store.contributors.authorization import Owner
from store.points.store import HistoryMedia, HistoryPage, HistoryPoint, PointCreation, PointStore

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
    return patch("store.points.store.session_scope", scope)


def _contributor(contributor_id="c-1", nickname="Ana"):
    return SimpleNamespace(id=contributor_id, nickname=nickname, removed_at=None)


async def _create(map_id="map-1", user_id="user-1", latitude=-34.6, longitude=-58.38, time=_TIME,
                  message="Calle inundada"):
    return await PointStore.create_point(
        map_id=map_id,
        author=Owner(user_id=user_id, username="joaco"),
        latitude=latitude,
        longitude=longitude,
        time=time,
        message=message,
    )


async def _create_as_contributor(contributor=None, map_id="map-1", time=_TIME):
    return await PointStore.create_point(
        map_id=map_id,
        author=contributor or _contributor(),
        latitude=-34.6,
        longitude=-58.38,
        time=time,
        message="Calle inundada",
    )


def _insert_params(db):
    return db.execute.call_args_list[-1].args[0].compile(dialect=postgresql.dialect()).params


async def _owner_id(**overrides):
    with _patch_scope(_db("p")):
        return (await _create(**overrides)).id


# ---- create_point as the owner ----

async def test_create_saves_a_new_point():
    db = _db("p-1")

    with _patch_scope(db):
        creation = await _create()

    assert creation.created is True
    db.commit.assert_called_once()


async def test_create_maps_the_fields_to_the_point_columns():
    db = _db("p-1")

    with _patch_scope(db):
        creation = await _create()

    params = _insert_params(db)
    assert params["id"] == creation.id
    assert params["map_id"] == "map-1"
    assert params["geom"] == "POINT(-58.38 -34.6)"
    assert params["message"] == "Calle inundada"
    assert params["username"] == "joaco"
    assert params["contributor_id"] is None


async def test_create_stores_the_time_in_utc_without_timezone():
    db = _db("p-1")

    with _patch_scope(db):
        await _create()

    assert _insert_params(db)["time"] == datetime(2026, 10, 7, 15, 15, 23)


async def test_create_answers_the_same_id_when_the_point_already_exists():
    db = _db(None)

    with _patch_scope(db):
        creation = await _create()

    assert creation.created is False
    assert creation.id == await _owner_id()
    db.commit.assert_called_once()


async def test_create_rolls_back_when_saving_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _create()

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ---- the id is derived from the data ----

async def test_the_id_is_a_sha256_hex_digest():
    assert re.fullmatch(r"[0-9a-f]{64}", await _owner_id())


async def test_the_same_data_gives_the_same_id():
    assert await _owner_id() == await _owner_id()


@pytest.mark.parametrize("overrides", [
    {"map_id": "map-2"},
    {"latitude": -34.7},
    {"longitude": -58.39},
    {"time": _TIME + timedelta(seconds=1)},
    {"message": "Calle seca"},
    {"message": None},
])
async def test_a_different_value_gives_a_different_id(overrides):
    assert await _owner_id(**overrides) != await _owner_id()


async def test_two_senders_with_the_same_data_get_different_ids():
    assert await _owner_id(user_id="user-2") != await _owner_id(user_id="user-1")


async def test_the_same_instant_in_another_offset_gives_the_same_id():
    same_instant = _TIME.astimezone(timezone.utc)

    assert await _owner_id(time=same_instant) == await _owner_id()


async def test_an_empty_message_gives_the_same_id_as_no_message():
    assert await _owner_id(message="") == await _owner_id(message=None)


async def test_an_owner_and_a_contributor_never_share_an_id():
    with _patch_scope(_db("p")):
        contributor_creation = await _create_as_contributor(_contributor("c-1"))

    assert contributor_creation.id != await _owner_id(user_id="c-1")


# ---- create_point as a contributor ----

async def test_contributor_create_saves_the_point_with_the_contributor_and_their_nickname():
    db = _db("p-1")

    with _patch_scope(db):
        creation = await _create_as_contributor(_contributor("c-1", "Ana"))

    params = _insert_params(db)
    assert creation.created is True
    assert params["id"] == creation.id
    assert params["contributor_id"] == "c-1"
    assert params["username"] == "Ana"
    assert params["map_id"] == "map-1"
    db.commit.assert_called_once()


async def test_contributor_create_answers_the_same_id_on_a_retry():
    with _patch_scope(_db("p-1")):
        first = await _create_as_contributor()

    with _patch_scope(_db(None)):
        retry = await _create_as_contributor()

    assert first.created is True
    assert retry == PointCreation(id=first.id, created=False)


async def test_two_contributors_with_the_same_data_get_different_ids():
    with _patch_scope(_db("p")):
        first = await _create_as_contributor(_contributor("c-1"))

    with _patch_scope(_db("p")):
        second = await _create_as_contributor(_contributor("c-2"))

    assert first.id != second.id


async def test_contributor_create_accepts_a_time_in_the_future():
    future = datetime.now(timezone.utc) + timedelta(days=1)

    with _patch_scope(_db("p-1")):
        creation = await _create_as_contributor(time=future)

    assert creation.created is True


async def test_contributor_create_rolls_back_when_saving_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _create_as_contributor()

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ---- contributor_points ----

def _history_result(*rows):
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def _history_db(*rows):
    db = MagicMock()
    db.execute.return_value = _history_result(*rows)
    return db


def _history_row(index, media=False, media_captured=True):
    when = datetime(2026, 10, 7, 15, 0, 0) - timedelta(minutes=index)
    media_time = when + timedelta(minutes=2) if media_captured else None
    media_columns = (f"m-{index}", "image/jpeg", 1000 + index, media_time) if media else (None, None, None, None)
    return (f"p-{index:03}", when, -34.6 - index / 1000, -58.38, f"note {index}", *media_columns)


def _cursor_of(payload):
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


async def _history(cursor=None, map_id="map-1", contributor=None):
    return await PointStore.contributor_points(
        map_id=map_id, contributor=contributor or _contributor(), cursor=cursor,
    )


def _history_query(db):
    return db.execute.call_args.args[0].compile(dialect=postgresql.dialect())


async def test_history_returns_the_points_with_their_coordinates_media_and_utc_time():
    db = _history_db(_history_row(0, media=True), _history_row(1))

    with _patch_scope(db):
        page = await _history()

    assert page == HistoryPage(
        points=[
            HistoryPoint(
                id="p-000",
                time=datetime(2026, 10, 7, 15, 0, 0, tzinfo=timezone.utc),
                latitude=-34.6,
                longitude=-58.38,
                message="note 0",
                media=HistoryMedia(
                    id="m-0",
                    content_type="image/jpeg",
                    size=1000,
                    captured_at=datetime(2026, 10, 7, 15, 2, 0, tzinfo=timezone.utc),
                ),
            ),
            HistoryPoint(
                id="p-001",
                time=datetime(2026, 10, 7, 14, 59, 0, tzinfo=timezone.utc),
                latitude=-34.601,
                longitude=-58.38,
                message="note 1",
                media=None,
            ),
        ],
        next=None,
    )


async def test_history_leaves_the_capture_time_empty_for_media_uploaded_before_it_was_recorded():
    with _patch_scope(_history_db(_history_row(0, media=True, media_captured=False))):
        page = await _history()

    assert page.points[0].media.captured_at is None


async def test_history_is_empty_when_the_contributor_has_no_points():
    with _patch_scope(_history_db()):
        page = await _history()

    assert page == HistoryPage(points=[], next=None)


async def test_history_asks_for_the_points_of_this_contributor_in_this_map_newest_first():
    db = _history_db()

    with _patch_scope(db):
        await _history(contributor=_contributor("c-7"))

    compiled = _history_query(db)
    sql = str(compiled)
    assert {"map-1", "c-7"} <= set(compiled.params.values())
    assert "points.removed IS false" in sql
    assert "ORDER BY points.time DESC, points.id DESC" in sql
    assert 51 in compiled.params.values()
    assert "points.time, points.id) <" not in sql


async def test_history_gives_a_page_of_fifty_and_a_cursor_when_there_are_more():
    with _patch_scope(_history_db(*[_history_row(index) for index in range(51)])):
        page = await _history()

    assert len(page.points) == 50
    assert page.points[-1].id == "p-049"
    assert page.next is not None


async def test_history_gives_no_cursor_when_the_page_is_the_last_one():
    with _patch_scope(_history_db(*[_history_row(index) for index in range(50)])):
        page = await _history()

    assert len(page.points) == 50
    assert page.next is None


async def test_history_continues_after_the_last_point_of_the_previous_page():
    with _patch_scope(_history_db(*[_history_row(index) for index in range(51)])):
        first = await _history()

    second_db = _history_db()

    with _patch_scope(second_db):
        await _history(cursor=first.next)

    compiled = _history_query(second_db)
    assert "(points.time, points.id) <" in str(compiled)
    assert {datetime(2026, 10, 7, 14, 11, 0), "p-049"} <= set(compiled.params.values())


@pytest.mark.parametrize("cursor", [
    "",
    "not base64!",
    _cursor_of([]),
    _cursor_of(["2026-10-07T15:00:00"]),
    _cursor_of([1, 2]),
    _cursor_of(["not a time", "p-1"]),
    _cursor_of(["2026-10-07T15:00:00+00:00", "p-1"]),
    _cursor_of(5),
    base64.urlsafe_b64encode(b"not json").decode(),
])
async def test_history_rejects_an_invalid_cursor_before_touching_the_database(cursor):
    db = MagicMock()

    with _patch_scope(db):
        with pytest.raises(InvalidCursor):
            await _history(cursor=cursor)

    db.execute.assert_not_called()


async def test_history_reports_the_store_unavailable_when_the_query_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _history()
