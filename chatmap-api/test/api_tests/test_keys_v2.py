from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.v2.routes.keys import create_key, read_keys, read_tags, set_point_tag, update_key
from api.v2.schemas.keys import MAX_KEY_VALUES, KeyChanges, KeyValueItem, NewKey, PointTagChange
from results.error import (
    ArchivedValue,
    BuiltinKey,
    InvalidTagValue,
    KeyInUse,
    KeyNameTaken,
    NotAuthorized,
    StoreUnavailable,
    UnknownKey,
    UnknownValue,
    ValueInUse,
)

SINCE = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
CONFIRMED = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _key(key_id="k-1", key="Fuel", single=True, closed=True, builtin=False, archived_at=None, colors_map=False):
    return SimpleNamespace(
        id=key_id, key=key, single=single, closed=closed, builtin=builtin, archived_at=archived_at,
        colors_map=colors_map,
    )


def _value(value_id="v-1", name="There is", color="#3E9E47", expires_after=None):
    return SimpleNamespace(
        id=value_id, value=name, description="", color=color, expires_after=expires_after, archived_at=None,
    )


def _tag(point_id="p-1", key_id="k-1", value_id="v-1", value=None):
    return SimpleNamespace(
        point_id=point_id, key_id=key_id, value_id=value_id, value=value, since=SINCE, confirmed_at=CONFIRMED,
    )


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.keys.MapKeysStore.{method}", AsyncMock(**kwargs))


# ---- GET /v2/maps/{map_id}/keys ----

async def test_read_keys_returns_each_key_with_its_options():
    keys = [
        (_key("k-0", "status", builtin=True, colors_map=True), [_value("v-0", "Open")]),
        (_key(), [_value(expires_after=timedelta(hours=6)), _value("v-2", "None", color=None)]),
    ]

    with _patch_store("read_keys", return_value=keys) as store:
        result = await read_keys(map_id="map-1", user=None)

    store.assert_awaited_once_with("map-1", None)
    assert [(key.key, key.builtin, key.colors_map,
             [(value.name, value.color, value.expires_after) for value in key.values])
            for key in result.keys] == [
        ("status", True, True, [("Open", "#3E9E47", None)]),
        ("Fuel", False, False, [("There is", "#3E9E47", 6), ("None", None, None)]),
    ]


async def test_read_keys_does_not_find_a_map_the_user_cannot_see():
    with _patch_store("read_keys", return_value=None), pytest.raises(HTTPException) as raised:
        await read_keys(map_id="map-1", user=_user())

    assert raised.value.status_code == 404


# ---- POST, PUT, DELETE /v2/maps/{map_id}/keys ----

async def test_create_key_passes_the_key_and_its_options():
    new = NewKey(key=" Fuel ", values=[KeyValueItem(name="There is", expires_after=6)])

    with _patch_store("create_key", return_value=(_key(), [_value()])) as store:
        result = await create_key(map_id="map-1", key=new, user=_user())

    store.assert_awaited_once_with("map-1", "user-1", {
        "key": "Fuel", "single": True, "closed": True, "colors_map": False,
        "values": [{"id": None, "name": "There is", "description": "", "color": None, "expires_after": 6,
                    "archived": False}],
    }, 10)
    assert (result.id, result.key) == ("k-1", "Fuel")




@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (UnknownKey("k-9"), 404),
    (UnknownValue("v-9"), 404),
    (BuiltinKey("k-0"), 409),
    (KeyNameTaken("Fuel"), 409),
    (KeyInUse("k-1"), 409),
    (ValueInUse(["v-1"]), 409),
    (ArchivedValue("v-1"), 409),
    (InvalidTagValue("too many"), 422),
    (StoreUnavailable(), 503),
])
async def test_store_errors_are_told_over_http(error, status_code):
    with _patch_store("update_key", side_effect=error), pytest.raises(HTTPException) as raised:
        await update_key(map_id="map-1", key_id="k-1", changes=KeyChanges(), user=_user())

    assert raised.value.status_code == status_code


# ---- GET /v2/maps/{map_id}/tags, PUT /v2/points/{point_id}/tags/{key_id} ----

async def test_read_tags_returns_what_each_point_has():
    with _patch_store("read_tags", return_value=[_tag(), _tag(key_id="k-2", value_id=None, value="near the school")]):
        result = await read_tags(map_id="map-1", user=None)

    assert [(tag.point_id, tag.key_id, tag.value_id, tag.value) for tag in result.tags] == [
        ("p-1", "k-1", "v-1", None), ("p-1", "k-2", None, "near the school"),
    ]
    assert (result.tags[0].since, result.tags[0].confirmed_at) == (SINCE, CONFIRMED)


async def test_set_point_tag_passes_the_change():
    happened_at = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
    change = PointTagChange(value_id="v-1", happened_at=happened_at)

    with _patch_store("set_point_tag", return_value=[_tag()]) as store:
        result = await set_point_tag(point_id="p-1", key_id="k-1", change=change, user=_user())

    store.assert_awaited_once_with(
        "p-1", "k-1", "user-1", "set", value_id="v-1", value=None, happened_at=happened_at,
    )
    assert [tag.value_id for tag in result.tags] == ["v-1"]


# ---- what a key and a change may be ----

@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_a_key_name_needs_a_valid_length(name):
    with pytest.raises(ValidationError):
        NewKey(key=name)


def test_an_option_of_a_key_may_have_no_color():
    assert KeyValueItem(name="Hospital").color is None


@pytest.mark.parametrize("color", ["red", "#FFF", "#3E9E47; x"])
def test_an_option_color_must_be_a_hex_color(color):
    with pytest.raises(ValidationError):
        KeyValueItem(name="Hospital", color=color)


def test_options_of_a_key_cannot_repeat():
    with pytest.raises(ValidationError):
        NewKey(key="Category", values=[KeyValueItem(name="Hospital"), KeyValueItem(name="hospital")])


def test_a_key_takes_a_limited_number_of_options():
    with pytest.raises(ValidationError):
        NewKey(key="Category", values=[KeyValueItem(name=f"Option {i}") for i in range(MAX_KEY_VALUES + 1)])


def test_a_free_value_is_trimmed_and_has_a_maximum_length():
    assert PointTagChange(value="  near the school ").value == "near the school"
    with pytest.raises(ValidationError):
        PointTagChange(value="x" * 101)

