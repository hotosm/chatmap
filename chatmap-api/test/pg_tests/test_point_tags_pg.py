from datetime import datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from db import Map, MapKey, MapKeyValue, Point, PointTag, PointTagChange, SharePermission
from results.error import NotAuthorized, UnknownTagChange
from store.map_keys_store import MapKeysStore
from store.point_tags_store import PointTagsStore

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
            Point(id="p-9", map_id="map-2", message="Other map"),
        ])
        db.commit()
    return pg


async def _status(map_id="map-1"):
    """A key "Status" with two options, made like any other key."""
    key, values = await MapKeysStore.create_key(map_id, OWNER, {
        "key": "Status", "single": True, "closed": True,
        "values": [{"value": "Open", "color": "#3E9E47"}, {"value": "Closed", "color": "#D73F3F"}],
    }, 10)
    return key, {value.value: value.id for value in values}


async def _give(key, value_id, time):
    return await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=value_id, happened_at=_at(time))


# ---- what the database keeps by itself ----

def _key_and_value(db):
    key = MapKey(id="k-1", map_id="map-1", key="Status", single=True, closed=True)
    db.add(key)
    db.flush()
    db.add_all([MapKeyValue(id="v-1", key_id="k-1", value="Open"), MapKeyValue(id="v-2", key_id="k-1", value="Closed")])
    db.flush()
    return key


def _tag(**fields):
    defaults = dict(point_id="p-1", key_id="k-1", single=True, since=_at("08:00"), confirmed_at=_at("08:00"), source="manual")
    return PointTag(**{**defaults, **fields})


def test_the_database_takes_one_value_per_point_for_a_single_key(world):
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


def test_the_database_does_not_repeat_a_free_value(world):
    with world() as db:
        db.add(MapKey(id="k-2", map_id="map-1", key="Notes", single=False, closed=False))
        db.flush()
        db.add(_tag(key_id="k-2", single=False, value="near the school"))
        db.flush()
        db.add(_tag(key_id="k-2", single=False, value="near the school"))
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


# ---- changes and history ----

async def test_a_change_is_written_down(world):
    key, ids = await _status()

    [tag] = await _give(key, ids["Open"], "08:30")

    assert (tag.value_id, tag.since, tag.confirmed_at, tag.source, tag.user_id) == (
        ids["Open"], _at("08:30"), _at("08:30"), "manual", OWNER,
    )
    with world() as db:
        [change] = db.execute(select(PointTagChange)).scalars().all()
    assert (change.action, change.value_id, change.value, change.happened_at) == ("set", ids["Open"], "Open", _at("08:30"))


async def test_a_change_that_happened_before_the_last_one_only_goes_to_history(world):
    key, ids = await _status()
    await _give(key, ids["Open"], "08:30")

    [tag] = await _give(key, ids["Closed"], "07:50")

    assert (tag.value_id, tag.since) == (ids["Open"], _at("08:30"))
    assert len(await PointTagsStore.history("p-1", OWNER)) == 2


async def test_undoing_the_last_change_gives_back_the_one_before(world):
    key, ids = await _status()
    await _give(key, ids["Open"], "08:30")
    await _give(key, ids["Closed"], "09:00")
    [(last, name), _] = await PointTagsStore.history("p-1", OWNER)

    change, _ = await PointTagsStore.set_undone(last.id, OWNER, True)

    assert (name, change.undone_by) == ("Status", OWNER)
    [tag] = await PointTagsStore.read_tags("map-1", OWNER)
    assert (tag.value_id, tag.since) == (ids["Open"], _at("08:30"))


async def test_restoring_a_change_brings_it_back(world):
    key, ids = await _status()
    await _give(key, ids["Open"], "08:30")
    await _give(key, ids["Closed"], "09:00")
    [(last, _), _] = await PointTagsStore.history("p-1", OWNER)
    await PointTagsStore.set_undone(last.id, OWNER, True)

    change, _ = await PointTagsStore.set_undone(last.id, OWNER, False)

    assert change.undone_at is None
    [tag] = await PointTagsStore.read_tags("map-1", OWNER)
    assert tag.value_id == ids["Closed"]


async def test_an_undone_change_stays_in_history(world):
    key, ids = await _status()
    await _give(key, ids["Open"], "08:30")
    [(change, _)] = await PointTagsStore.history("p-1", OWNER)

    await PointTagsStore.set_undone(change.id, OWNER, True)

    [(kept, _)] = await PointTagsStore.history("p-1", OWNER)
    assert kept.undone_at is not None


async def test_only_the_owner_sees_the_history_and_undoes(world):
    key, ids = await _status()
    await _give(key, ids["Open"], "08:30")
    [(change, _)] = await PointTagsStore.history("p-1", OWNER)

    with pytest.raises(NotAuthorized):
        await PointTagsStore.history("p-1", "someone-else")
    with pytest.raises(NotAuthorized):
        await PointTagsStore.set_undone(change.id, "someone-else", True)


async def test_undoing_an_unknown_change_fails(world):
    with pytest.raises(UnknownTagChange):
        await PointTagsStore.set_undone(999, OWNER, True)


# ---- who sees what ----

async def test_a_private_map_does_not_show_its_keys_nor_tags_to_others(world):
    await _status("map-2")

    assert await MapKeysStore.read_keys("map-2", "someone-else") is None
    assert await PointTagsStore.read_tags("map-2", None) is None


# ---- removing points and maps ----

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
    key, ids = await _status()
    await _give(key, ids["Open"], "08:30")

    with world() as db:
        db.delete(db.get(Map, "map-1"))
        db.commit()

        for table in ("map_keys", "map_key_values", "point_tags", "point_tag_changes"):
            assert db.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0, table
        # The other map is untouched
        assert db.get(Point, "p-9") is not None
