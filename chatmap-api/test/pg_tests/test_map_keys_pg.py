from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import Map, MapKey, Point, PointTagChange, SharePermission, add_points
from results.error import (
    ArchivedValue,
    InvalidTagValue,
    KeyInUse,
    KeyNameTaken,
    NotAuthorized,
    TooManyKeys,
    UnknownKey,
    UnknownValue,
    ValueInUse,
)
from store.map_keys_store import MapKeysStore
from store.point_tags_store import PointTagsStore

OWNER = "user-1"
MAX_KEYS = 10


def _at(time):
    return datetime.fromisoformat(f"2026-10-06T{time}:00+00:00")


@pytest.fixture
def world(pg):
    """Two maps of the same owner, with points: all made up."""
    with pg() as db:
        db.add_all([
            Map(id="map-1", owner_id=OWNER, sharing=SharePermission.PUBLIC, is_live=True),
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


def _fuel(**fields):
    return {
        "key": "Fuel", "single": True, "closed": True,
        "values": [
            {"value": "There is", "color": "#3E9E47", "expires_after": 6},
            {"value": "There is not", "color": "#D73F3F", "expires_after": 12},
        ],
        **fields,
    }


async def _create(map_id="map-1", **fields):
    key, values = await MapKeysStore.create_key(map_id, OWNER, _fuel(**fields), MAX_KEYS)
    return key, {value.value: value.id for value in values}


# ---- keys of a map ----

async def test_a_key_is_created_with_its_values(world):
    key, values = await MapKeysStore.create_key("map-1", OWNER, _fuel(), MAX_KEYS)

    assert (key.key, key.single, key.closed, key.colors_map) == ("Fuel", True, True, False)
    assert [(value.value, value.color, value.expires_after) for value in values] == [
        ("There is", "#3E9E47", timedelta(hours=6)), ("There is not", "#D73F3F", timedelta(hours=12)),
    ]


async def test_a_value_does_not_need_a_color_nor_to_expire(world):
    _, values = await MapKeysStore.create_key(
        "map-1", OWNER, {"key": "Category", "single": True, "closed": True, "values": [{"value": "Hospital"}]},
        MAX_KEYS,
    )

    assert [(value.value, value.color, value.expires_after) for value in values] == [("Hospital", None, None)]


async def test_a_free_key_has_no_values(world):
    with pytest.raises(InvalidTagValue):
        await MapKeysStore.create_key(
            "map-1", OWNER, {"key": "Notes", "single": False, "closed": False, "values": [{"value": "x"}]}, MAX_KEYS,
        )


@pytest.mark.parametrize("name", ["fuel", "FUEL"])
async def test_a_key_name_is_once_per_map_whatever_its_case(world, name):
    await _create()

    with pytest.raises(KeyNameTaken):
        await MapKeysStore.create_key("map-1", OWNER, _fuel(key=name), MAX_KEYS)



async def test_a_map_takes_a_limited_number_of_keys(world):
    for number in range(2):
        await MapKeysStore.create_key("map-1", OWNER, _fuel(key=f"Key {number}"), 2)

    with pytest.raises(TooManyKeys):
        await MapKeysStore.create_key("map-1", OWNER, _fuel(key="One more"), 2)


async def test_only_the_owner_creates_keys(world):
    with pytest.raises(NotAuthorized):
        await MapKeysStore.create_key("map-1", "someone-else", _fuel(), MAX_KEYS)




async def test_a_key_is_renamed_and_its_values_edited(world):
    key, values = await _create()

    row, saved = await MapKeysStore.update_key("map-1", key.id, OWNER, {
        "key": "Gasoline",
        "values": [
            {"id": values["There is not"], "value": "None", "color": "#D73F3F"},
            {"id": values["There is"], "value": "There is", "color": "#3E9E47", "expires_after": 3},
            {"value": "Little"},
        ],
    })

    assert row.key == "Gasoline"
    assert [(value.id, value.value, value.expires_after) for value in saved] == [
        (values["There is not"], "None", None), (values["There is"], "There is", timedelta(hours=3)),
        (saved[2].id, "Little", None),
    ]



async def test_a_value_some_point_has_is_not_removed(world):
    key, values = await _create()
    await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=values["There is"])

    with pytest.raises(ValueInUse):
        await MapKeysStore.update_key("map-1", key.id, OWNER, {"values": [{"value": "Other"}]})


async def test_a_key_never_used_is_removed(world):
    key, _ = await _create()

    await MapKeysStore.remove_key("map-1", key.id, OWNER)

    assert await MapKeysStore.read_keys("map-1", OWNER) == []


async def test_a_key_that_was_used_is_only_archived(world):
    key, values = await _create()
    await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=values["There is"])
    await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "remove")

    with pytest.raises(KeyInUse):
        await MapKeysStore.remove_key("map-1", key.id, OWNER)
    row, _ = await MapKeysStore.update_key("map-1", key.id, OWNER, {"archived": True})
    assert row.archived_at is not None


async def test_a_key_of_another_map_is_not_found(world):
    key, _ = await _create("map-2")

    with pytest.raises(UnknownKey):
        await MapKeysStore.update_key("map-1", key.id, OWNER, {"key": "Other"})


# ---- the key that colors the map ----

async def _colors(map_id="map-1"):
    return [key.key for key, _ in await MapKeysStore.read_keys(map_id, OWNER) if key.colors_map]




async def test_choosing_a_key_to_color_the_map_unchooses_the_other(world):
    await _create(key="Status", colors_map=True)
    key, _ = await _create()

    await MapKeysStore.update_key("map-1", key.id, OWNER, {"colors_map": True})

    assert await _colors() == ["Fuel"]


async def test_a_map_can_be_colored_by_no_key(world):
    key, _ = await _create(colors_map=True)

    await MapKeysStore.update_key("map-1", key.id, OWNER, {"colors_map": False})

    assert await _colors() == []


def test_the_database_takes_one_key_coloring_a_map(world):
    with world() as db:
        db.add(MapKey(map_id="map-1", key="One", single=True, closed=True, colors_map=True))
        db.flush()
        db.add(MapKey(map_id="map-1", key="Two", single=True, closed=True, colors_map=True))
        with pytest.raises(IntegrityError):
            db.flush()


# ---- the tags of a point ----


async def test_a_key_with_one_value_keeps_the_last_one(world):
    key, values = await _create()
    await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=values["There is"], happened_at=_at("08:00"))

    tags = await PointTagsStore.set_point_tag(
        "p-1", key.id, OWNER, "set", value_id=values["There is not"], happened_at=_at("09:00"),
    )

    assert [tag.value_id for tag in tags] == [values["There is not"]]


async def test_a_key_with_many_options_keeps_each_one(world):
    key, values = await _create(key="Services", single=False, values=[{"value": "Water"}, {"value": "Food"}])
    await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=values["Water"])
    tags = await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=values["Food"])

    assert sorted(tag.value_id for tag in tags) == sorted([values["Water"], values["Food"]])
    tags = await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "remove", value_id=values["Water"])
    assert [tag.value_id for tag in tags] == [values["Food"]]


async def test_a_free_key_takes_texts(world):
    key, _ = await _create(key="Notes", single=False, closed=False, values=[])
    await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value="checked by the team")
    tags = await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value="near the school")

    assert sorted(tag.value for tag in tags) == ["checked by the team", "near the school"]
    assert all(tag.value_id is None for tag in tags)


@pytest.mark.parametrize("change, error", [
    ({"action": "set"}, InvalidTagValue),
    ({"action": "set", "value": "There is"}, InvalidTagValue),
    ({"action": "set", "value_id": "v-unknown"}, UnknownValue),
])
async def test_a_key_with_a_list_takes_one_of_its_options(world, change, error):
    key, _ = await _create()

    with pytest.raises(error):
        await PointTagsStore.set_point_tag("p-1", key.id, OWNER, change.pop("action"), **change)


async def test_an_option_of_another_key_is_not_taken(world):
    key, _ = await _create()
    _, others = await _create(key="Category", values=[{"value": "Hospital"}])

    with pytest.raises(UnknownValue):
        await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=others["Hospital"])


async def test_an_archived_option_is_not_given(world):
    key, values = await _create(values=[{"value": "Old", "archived": True}])

    with pytest.raises(ArchivedValue):
        await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=values["Old"])


async def test_a_point_does_not_take_a_key_of_another_map(world):
    key, values = await _create("map-2")

    with pytest.raises(UnknownKey):
        await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "set", value_id=values["There is"])



async def test_only_the_owner_gives_tags(world):
    key, values = await _create()

    with pytest.raises(NotAuthorized):
        await PointTagsStore.set_point_tag("p-1", key.id, "someone-else", "set", value_id=values["There is"])


async def test_taking_out_what_a_point_does_not_have_writes_nothing(world):
    key, values = await _create()

    assert await PointTagsStore.set_point_tag("p-1", key.id, OWNER, "remove") == []
    with world() as db:
        assert db.execute(select(PointTagChange)).first() is None


# ---- reading the tags of a map ----

async def test_reading_the_tags_of_a_map(world):
    fuel, values = await _create()
    status, statuses = await _create(key="Status", values=[{"value": "Open"}])
    await PointTagsStore.set_point_tag("p-1", status.id, OWNER, "set", value_id=statuses["Open"])
    await PointTagsStore.set_point_tag("p-1", fuel.id, OWNER, "set", value_id=values["There is"])
    await PointTagsStore.set_point_tag("p-2", fuel.id, OWNER, "set", value_id=values["There is"])

    for_owner = await PointTagsStore.read_tags("map-1", OWNER)
    for_public = await PointTagsStore.read_tags("map-1", None)

    assert sorted((tag.point_id, tag.value_id) for tag in for_owner) == sorted([
        ("p-1", statuses["Open"]), ("p-1", values["There is"]), ("p-2", values["There is"]),
    ])
    # Removed points are only shown to the owner
    assert [tag.point_id for tag in for_public] == ["p-1", "p-1"]


# ---- a point that moves to another map ----

async def test_a_point_moving_to_another_map_leaves_its_tags_behind(world):
    key, values = await _create("map-2")
    await PointTagsStore.set_point_tag("p-9", key.id, OWNER, "set", value_id=values["There is"])

    # The mapper writes p-9 again, now to the live map of the owner (map-1)
    with world() as db:
        add_points(db, [{"id": "p-9", "message": "Other map", "time": datetime(2026, 10, 6, 9, 0)}], OWNER)
        moved = db.get(Point, "p-9").map_id
        changes = db.execute(
            select(PointTagChange.action, PointTagChange.source).order_by(PointTagChange.id)
        ).all()

    assert moved == "map-1"
    assert changes == [("set", "manual"), ("remove", "system")]
    assert await PointTagsStore.read_tags("map-2", OWNER) == []


def test_points_that_stay_in_their_map_keep_their_tags(world):
    with world() as db:
        add_points(db, [{"id": "p-1", "message": "South access", "time": datetime(2026, 10, 6, 9, 0)}], OWNER)

        assert db.execute(select(PointTagChange)).first() is None
