from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from db import Map, MapKey, MapKeyValue, Point, PointTag, PointTagChange, SharePermission
from results.error import (
    ArchivedStatus,
    NotAuthorized,
    StatusInUse,
    UnknownStatus,
    UnknownTagChange,
)
from store.map_statuses_store import MapStatusesStore
from store.point_tags_store import PointTagsStore

GREEN = "#3E9E47"
RED = "#D73F3F"
OWNER = "user-1"


def _at(time):
    return datetime.fromisoformat(f"2026-10-06T{time}:00+00:00")


@pytest.fixture
def world(pg):
    """Two maps of the same owner, with a point each: all made up."""
    with pg() as db:
        db.add_all([
            Map(id="map-1", owner_id=OWNER, sharing=SharePermission.PUBLIC),
            Map(id="map-2", owner_id=OWNER),
        ])
        db.flush()
        db.add_all([
            Point(id="p-1", map_id="map-1", message="South access"),
            Point(id="p-2", map_id="map-1", message="North access", removed=True),
            Point(id="p-9", map_id="map-2", message="Other map"),
        ])
        db.commit()
    return pg


async def _statuses(map_id="map-1", *names, archived=()):
    statuses = [
        {"name": name, "color": GREEN, "expires_after": 4 if name == "Open" else None, "archived": name in archived}
        for name in names or ("Open", "Closed")
    ]
    return {row.value: row.id for row in await MapStatusesStore.set_statuses(map_id, OWNER, statuses)}


# ---- what the database keeps by itself ----

def _key_and_value(db):
    key = MapKey(id="k-1", map_id="map-1", key="status", single=True, closed=True)
    db.add(key)
    db.flush()
    db.add_all([MapKeyValue(id="v-1", key_id="k-1", value="Open"), MapKeyValue(id="v-2", key_id="k-1", value="Closed")])
    db.flush()
    return key


def _tag(**fields):
    defaults = dict(point_id="p-1", key_id="k-1", single=True, since=_at("08:00"), confirmed_at=_at("08:00"), source="manual")
    return PointTag(**{**defaults, **fields})


def test_the_database_takes_one_status_per_point(world):
    with world() as db:
        _key_and_value(db)
        db.add(_tag(value_id="v-1"))
        db.flush()
        db.add(_tag(value_id="v-2"))
        with pytest.raises(IntegrityError):
            db.flush()


def test_the_database_does_not_let_a_row_pass_as_one_of_many_values(world):
    with world() as db:
        _key_and_value(db)
        db.add(_tag(value_id="v-1"))
        db.flush()
        # The copy of "single" has to be the one of the key
        db.add(_tag(value_id="v-2", single=False))
        with pytest.raises(IntegrityError):
            db.flush()


def test_the_database_does_not_repeat_a_free_tag(world):
    with world() as db:
        db.add(MapKey(id="k-2", map_id="map-1", key="tag", single=False, closed=False))
        db.flush()
        db.add(_tag(key_id="k-2", single=False, value="guard"))
        db.add(_tag(key_id="k-2", single=False, value="pediatrics"))
        db.flush()
        db.add(_tag(key_id="k-2", single=False, value="guard"))
        with pytest.raises(IntegrityError):
            db.flush()


@pytest.mark.parametrize("fields", [{}, {"value_id": "v-1", "value": "Open"}])
def test_the_database_takes_exactly_one_value(world, fields):
    with world() as db:
        _key_and_value(db)
        db.add(_tag(**fields))
        with pytest.raises(IntegrityError):
            db.flush()


def test_the_database_does_not_remove_a_value_some_point_has(world):
    with world() as db:
        _key_and_value(db)
        db.add(_tag(value_id="v-1"))
        db.flush()
        with pytest.raises(IntegrityError):
            db.execute(text("DELETE FROM map_key_values WHERE id = 'v-1'"))


def test_the_database_does_not_repeat_a_value_of_a_key_whatever_its_case(world):
    with world() as db:
        _key_and_value(db)
        db.add(MapKeyValue(key_id="k-1", value="OPEN"))
        with pytest.raises(IntegrityError):
            db.flush()


# ---- the statuses of a map ----

async def test_the_first_status_creates_the_status_key_of_the_map(world):
    ids = await _statuses("map-1", "Open", "Closed")

    with world() as db:
        key = db.execute(select(MapKey).where(MapKey.map_id == "map-1")).scalar_one()
        values = db.execute(select(MapKeyValue).order_by(MapKeyValue.position)).scalars().all()
    assert (key.key, key.single, key.closed, key.builtin) == ("status", True, True, True)
    assert [(value.id, value.value, value.expires_after) for value in values] == [
        (ids["Open"], "Open", timedelta(hours=4)), (ids["Closed"], "Closed", None),
    ]


async def test_editing_the_statuses_keeps_their_ids(world):
    ids = await _statuses("map-1", "Open", "Closed")

    rows = await MapStatusesStore.set_statuses("map-1", OWNER, [
        {"id": ids["Closed"], "name": "Closed for good", "color": RED},
        {"id": ids["Open"], "name": "Open", "color": GREEN, "expires_after": 2},
    ])

    assert [(row.id, row.value, row.expires_after) for row in rows] == [
        (ids["Closed"], "Closed for good", None), (ids["Open"], "Open", timedelta(hours=2)),
    ]


async def test_an_id_of_another_map_is_taken_as_a_new_status(world):
    other = await _statuses("map-2", "Open")

    rows = await MapStatusesStore.set_statuses("map-1", OWNER, [{"id": other["Open"], "name": "Open", "color": GREEN}])

    assert rows[0].id != other["Open"]


async def test_only_the_owner_sets_the_statuses(world):
    with pytest.raises(NotAuthorized):
        await MapStatusesStore.set_statuses("map-1", "someone-else", [{"name": "Open", "color": GREEN}])


async def test_a_status_some_point_has_is_not_removed(world):
    ids = await _statuses("map-1", "Open", "Closed")
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Closed"])

    with pytest.raises(StatusInUse) as raised:
        await MapStatusesStore.set_statuses("map-1", OWNER, [{"id": ids["Open"], "name": "Open", "color": GREEN}])

    assert raised.value.status_ids == [ids["Closed"]]


async def test_archiving_keeps_the_date_it_was_archived(world):
    ids = await _statuses("map-1", "Open", "Closed", archived=("Closed",))
    [first] = [row.archived_at for row in await MapStatusesStore.statuses_for("map-1") if row.id == ids["Closed"]]

    rows = await MapStatusesStore.set_statuses("map-1", OWNER, [
        {"id": ids["Open"], "name": "Open", "color": GREEN},
        {"id": ids["Closed"], "name": "Closed", "color": RED, "archived": True},
    ])

    assert first is not None
    assert [row.archived_at for row in rows if row.id == ids["Closed"]] == [first]


# ---- the status of a point ----

async def test_a_point_takes_a_status_and_its_change_is_written_down(world):
    ids = await _statuses()

    tag = await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))

    assert (tag.value_id, tag.since, tag.confirmed_at, tag.source, tag.user_id) == (
        ids["Open"], _at("08:30"), _at("08:30"), "manual", OWNER,
    )
    with world() as db:
        [change] = db.execute(select(PointTagChange)).scalars().all()
    assert (change.action, change.value_id, change.value, change.happened_at) == ("set", ids["Open"], "Open", _at("08:30"))



async def test_a_status_that_happened_before_the_last_one_only_goes_to_history(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))

    tag = await MapStatusesStore.set_point_status("p-1", OWNER, ids["Closed"], _at("07:50"))

    assert (tag.value_id, tag.since) == (ids["Open"], _at("08:30"))
    assert len(await PointTagsStore.history("p-1", OWNER)) == 2


async def test_a_point_can_be_left_without_status(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))

    assert await MapStatusesStore.set_point_status("p-1", OWNER, None, _at("09:00")) is None
    _, points = await MapStatusesStore.read_statuses("map-1", OWNER)
    assert points == []


async def test_a_point_does_not_take_a_status_of_another_map(world):
    await _statuses("map-1")
    other = await _statuses("map-2", "Open")

    with pytest.raises(UnknownStatus):
        await MapStatusesStore.set_point_status("p-1", OWNER, other["Open"])


async def test_a_point_does_not_take_an_archived_status(world):
    ids = await _statuses("map-1", "Open", "Closed", archived=("Closed",))

    with pytest.raises(ArchivedStatus):
        await MapStatusesStore.set_point_status("p-1", OWNER, ids["Closed"])


async def test_only_the_owner_gives_a_status(world):
    ids = await _statuses()

    with pytest.raises(NotAuthorized):
        await MapStatusesStore.set_point_status("p-1", "someone-else", ids["Open"])


# ---- reading the statuses of a map ----

async def test_reading_tells_since_and_confirmed_of_each_point(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("11:00"))

    statuses, points = await MapStatusesStore.read_statuses("map-1", OWNER)

    assert [status.value for status in statuses] == ["Open", "Closed"]
    assert [(point.point_id, point.value_id, point.since, point.confirmed_at) for point in points] == [
        ("p-1", ids["Open"], _at("08:30"), _at("11:00")),
    ]


async def test_removed_points_are_only_shown_to_the_owner(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-2", OWNER, ids["Open"])

    _, for_owner = await MapStatusesStore.read_statuses("map-1", OWNER)
    _, for_public = await MapStatusesStore.read_statuses("map-1", None)

    assert [point.point_id for point in for_owner] == ["p-2"]
    assert for_public == []


async def test_a_private_map_is_not_read_by_others(world):
    await _statuses("map-2", "Open")

    assert await MapStatusesStore.read_statuses("map-2", "someone-else") is None


async def test_a_map_without_statuses_reads_empty(world):
    assert await MapStatusesStore.read_statuses("map-1", OWNER) == ([], [])


# ---- history, undo and restore ----

async def test_undoing_the_last_change_gives_back_the_one_before(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Closed"], _at("09:00"))
    [(last, key), _] = await PointTagsStore.history("p-1", OWNER)

    change, _ = await PointTagsStore.set_undone(last.id, OWNER, True)

    assert (key, change.undone_by) == ("status", OWNER)
    _, points = await MapStatusesStore.read_statuses("map-1", OWNER)
    assert [(point.value_id, point.since) for point in points] == [(ids["Open"], _at("08:30"))]


async def test_restoring_a_change_brings_it_back(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Closed"], _at("09:00"))
    [(last, _), _] = await PointTagsStore.history("p-1", OWNER)
    await PointTagsStore.set_undone(last.id, OWNER, True)

    change, _ = await PointTagsStore.set_undone(last.id, OWNER, False)

    assert change.undone_at is None
    _, points = await MapStatusesStore.read_statuses("map-1", OWNER)
    assert [point.value_id for point in points] == [ids["Closed"]]


async def test_an_undone_change_stays_in_history(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))
    [(change, _)] = await PointTagsStore.history("p-1", OWNER)

    await PointTagsStore.set_undone(change.id, OWNER, True)

    [(kept, _)] = await PointTagsStore.history("p-1", OWNER)
    assert kept.undone_at is not None


async def test_only_the_owner_sees_the_history_and_undoes(world):
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"])
    [(change, _)] = await PointTagsStore.history("p-1", OWNER)

    with pytest.raises(NotAuthorized):
        await PointTagsStore.history("p-1", "someone-else")
    with pytest.raises(NotAuthorized):
        await PointTagsStore.set_undone(change.id, "someone-else", True)


async def test_undoing_an_unknown_change_fails(world):
    with pytest.raises(UnknownTagChange):
        await PointTagsStore.set_undone(999, OWNER, True)


def test_removing_a_point_removes_its_tags_and_history(world):
    with world() as db:
        _key_and_value(db)
        db.add(_tag(value_id="v-1"))
        db.add(PointTagChange(point_id="p-1", key_id="k-1", action="set", value_id="v-1", value="Open",
                              happened_at=_at("08:00"), source="manual"))
        db.commit()
        db.execute(text("DELETE FROM points WHERE id = 'p-1'"))
        db.commit()

        assert db.execute(text("SELECT count(*) FROM point_tags")).scalar() == 0
        assert db.execute(text("SELECT count(*) FROM point_tag_changes")).scalar() == 0


async def test_deleting_a_map_as_the_api_does_still_works(world):
    # main.py deletes a map with db.delete(map): its points go first, then the map
    ids = await _statuses()
    await MapStatusesStore.set_point_status("p-1", OWNER, ids["Open"], _at("08:30"))

    with world() as db:
        db.delete(db.get(Map, "map-1"))
        db.commit()

        for table in ("points", "map_keys", "map_key_values", "point_tags", "point_tag_changes"):
            count = db.execute(text(
                f"SELECT count(*) FROM {table}" + (" WHERE map_id = 'map-1'" if table in ("points", "map_keys") else "")
            )).scalar()
            assert count == 0, table
        # The other map is untouched
        assert db.get(Point, "p-9") is not None
