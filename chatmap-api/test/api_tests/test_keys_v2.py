from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.v2.routes.keys import create_key, read_keys
from api.v2.schemas.keys import MAX_KEY_VALUES, KeyValueItem, NewKey


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _key(key_id="k-1", key="Fuel", single=True, closed=True, archived_at=None, colors_map=False):
    return SimpleNamespace(
        id=key_id, key=key, single=single, closed=closed, archived_at=archived_at, colors_map=colors_map,
    )


def _value(value_id="v-1", name="There is", color="#3E9E47", expires_after=None):
    return SimpleNamespace(
        id=value_id, value=name, description="", color=color, expires_after=expires_after, archived_at=None,
    )


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.keys.MapKeysStore.{method}", AsyncMock(**kwargs))


# ---- GET /v2/maps/{map_id}/keys ----


async def test_read_keys_returns_each_key_with_its_values():
    keys = [
        (_key("k-0", "Status", colors_map=True), [_value("v-0", "Open")]),
        (_key(), [_value(expires_after=timedelta(hours=6)), _value("v-2", "None", color=None)]),
    ]

    with _patch_store("read_keys", return_value=keys) as store:
        result = await read_keys(map_id="map-1", user=None)

    store.assert_awaited_once_with("map-1", None)
    assert [(key.key, key.colors_map,
             [(value.value, value.color, value.expires_after) for value in key.values])
            for key in result.keys] == [
        ("Status", True, [("Open", "#3E9E47", None)]),
        ("Fuel", False, [("There is", "#3E9E47", 6), ("None", None, None)]),
    ]


async def test_read_keys_does_not_find_a_map_the_user_cannot_see():
    with _patch_store("read_keys", return_value=None), pytest.raises(HTTPException) as raised:
        await read_keys(map_id="map-1", user=_user())

    assert raised.value.status_code == 404


# ---- POST, PUT, DELETE /v2/maps/{map_id}/keys ----


async def test_create_key_passes_the_key_and_its_options():
    new = NewKey(key=" Fuel ", values=[KeyValueItem(value="There is", expires_after=6)])

    with _patch_store("create_key", return_value=(_key(), [_value()])) as store:
        result = await create_key(map_id="map-1", key=new, user=_user())

    store.assert_awaited_once_with("map-1", "user-1", {
        "key": "Fuel", "single": True, "closed": True, "colors_map": False,
        "values": [{"id": None, "value": "There is", "description": "", "color": None, "expires_after": 6,
                    "archived": False}],
    }, 10)
    assert (result.id, result.key) == ("k-1", "Fuel")


# ---- what a key may be ----


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_a_key_name_needs_a_valid_length(name):
    with pytest.raises(ValidationError):
        NewKey(key=name)


@pytest.mark.parametrize("color", ["red", "#FFF", "#3E9E47; x"])
def test_a_value_color_must_be_a_hex_color(color):
    with pytest.raises(ValidationError):
        KeyValueItem(value="Hospital", color=color)


def test_values_of_a_key_cannot_repeat():
    with pytest.raises(ValidationError):
        NewKey(key="Category", values=[KeyValueItem(value="Hospital"), KeyValueItem(value="hospital")])


def test_a_key_takes_a_limited_number_of_values():
    with pytest.raises(ValidationError):
        NewKey(key="Category", values=[KeyValueItem(value=f"Option {i}") for i in range(MAX_KEY_VALUES + 1)])

