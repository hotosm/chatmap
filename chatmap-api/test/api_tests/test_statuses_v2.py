from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.v2.routes.statuses import read_statuses, set_point_status, set_statuses
from api.v2.schemas.statuses import (
    MAX_STATUSES,
    MapStatuses,
    MapStatusItem,
    PointStatus,
)
from results.error import (
    ArchivedStatus,
    NotAuthorized,
    StatusInUse,
    StoreUnavailable,
    UnknownStatus,
)

GREEN = "#3E9E47"
RED = "#D73F3F"


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _row(status_id="s-1", name="Open", color=GREEN, description="", archived_at=None):
    return SimpleNamespace(id=status_id, name=name, color=color, description=description, archived_at=archived_at)


def _statuses(*items):
    return MapStatuses(statuses=[MapStatusItem(**item) for item in items])


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.statuses.MapStatusesStore.{method}", AsyncMock(**kwargs))


# ---- GET /v2/maps/{map_id}/statuses ----

async def test_read_returns_the_statuses_and_the_status_of_each_point():
    updated_at = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
    statuses = [_row("s-1", "Open"), _row("s-2", "Closed", RED, "Nobody can pass")]
    points = [SimpleNamespace(id="p-1", status_id="s-2", status_updated_at=updated_at)]

    with _patch_store("read_statuses", return_value=(statuses, points)) as store:
        result = await read_statuses(map_id="map-1", user=_user())

    store.assert_awaited_once_with("map-1", "user-1")
    assert [(status.id, status.name, status.description) for status in result.statuses] == [
        ("s-1", "Open", ""), ("s-2", "Closed", "Nobody can pass"),
    ]
    assert [(point.id, point.status, point.status_updated_at) for point in result.points] == [
        ("p-1", "s-2", updated_at),
    ]


async def test_read_tells_the_archived_statuses_apart():
    archived_at = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
    statuses = [_row("s-1", "Open"), _row("s-2", "Closed", RED, archived_at=archived_at)]

    with _patch_store("read_statuses", return_value=(statuses, [])):
        result = await read_statuses(map_id="map-1", user=_user())

    assert [(status.id, status.archived, status.archived_at) for status in result.statuses] == [
        ("s-1", False, None), ("s-2", True, archived_at),
    ]


async def test_read_works_without_a_user():
    with _patch_store("read_statuses", return_value=([], [])) as store:
        result = await read_statuses(map_id="map-1", user=None)

    store.assert_awaited_once_with("map-1", None)
    assert result.statuses == []
    assert result.points == []


async def test_read_does_not_find_a_map_the_user_cannot_see():
    with _patch_store("read_statuses", return_value=None), pytest.raises(HTTPException) as raised:
        await read_statuses(map_id="map-1", user=_user())

    assert raised.value.status_code == 404


async def test_read_reports_the_store_as_unavailable():
    with _patch_store("read_statuses", side_effect=StoreUnavailable()), pytest.raises(HTTPException) as raised:
        await read_statuses(map_id="map-1", user=_user())

    assert raised.value.status_code == 503


# ---- PUT /v2/maps/{map_id}/statuses ----

async def test_set_returns_the_statuses_as_they_were_saved():
    saved = [_row("s-1", "Open"), _row("s-2", "Closed", RED, "Nobody can pass")]

    with _patch_store("set_statuses", return_value=saved) as store:
        result = await set_statuses(
            map_id="map-1",
            statuses=_statuses({"name": "Open", "color": GREEN}, {"name": "Closed", "color": RED}),
            user=_user(),
        )

    store.assert_awaited_once_with("map-1", "user-1", [
        {"id": None, "name": "Open", "description": "", "color": GREEN, "archived": False},
        {"id": None, "name": "Closed", "description": "", "color": RED, "archived": False},
    ])
    assert [(status.id, status.name, status.description) for status in result.statuses] == [
        ("s-1", "Open", ""), ("s-2", "Closed", "Nobody can pass"),
    ]


@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (StatusInUse(["s-1"]), 409),
    (StoreUnavailable(), 503),
])
async def test_set_maps_store_errors_to_http(error, status_code):
    with _patch_store("set_statuses", side_effect=error), pytest.raises(HTTPException) as raised:
        await set_statuses(map_id="map-1", statuses=_statuses(), user=_user())

    assert raised.value.status_code == status_code


# ---- PUT /v2/points/{point_id}/status ----

async def test_set_point_status_returns_the_status_and_when_it_was_updated():
    updated_at = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)

    with _patch_store("set_point_status", return_value=("s-1", updated_at)) as store:
        result = await set_point_status(point_id="p-1", point_status=PointStatus(status="s-1"), user=_user())

    store.assert_awaited_once_with("p-1", "user-1", "s-1")
    assert result.status == "s-1"
    assert result.status_updated_at == updated_at


async def test_set_point_status_can_leave_a_point_without_status():
    with _patch_store("set_point_status", return_value=(None, None)) as store:
        result = await set_point_status(point_id="p-1", point_status=PointStatus(status=None), user=_user())

    store.assert_awaited_once_with("p-1", "user-1", None)
    assert result.status is None
    assert result.status_updated_at is None


@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (UnknownStatus("s-9"), 404),
    (ArchivedStatus("s-9"), 409),
    (StoreUnavailable(), 503),
])
async def test_set_point_status_maps_store_errors_to_http(error, status_code):
    with _patch_store("set_point_status", side_effect=error), pytest.raises(HTTPException) as raised:
        await set_point_status(point_id="p-1", point_status=PointStatus(status="s-9"), user=_user())

    assert raised.value.status_code == status_code


# ---- what a status may be ----

def test_a_status_name_is_trimmed():
    assert MapStatusItem(name="  Open  ", color=GREEN).name == "Open"


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_a_status_name_needs_a_valid_length(name):
    with pytest.raises(ValidationError):
        MapStatusItem(name=name, color=GREEN)


def test_a_status_description_has_a_maximum_length():
    with pytest.raises(ValidationError):
        MapStatusItem(name="Open", description="x" * 201, color=GREEN)


def test_a_status_takes_any_hex_color():
    assert MapStatusItem(name="Open", color="#1a2b3c").color == "#1A2B3C"


@pytest.mark.parametrize("color", ["red", "#FFF", "3E9E47", "#GGGGGG", "#3E9E47; background: url(x)", "#3E9E47\n"])
def test_a_status_color_must_be_a_hex_color(color):
    with pytest.raises(ValidationError):
        MapStatusItem(name="Open", color=color)


def test_status_names_cannot_repeat():
    with pytest.raises(ValidationError):
        _statuses({"name": "Open", "color": GREEN}, {"name": "open", "color": RED})


def test_a_map_takes_a_limited_number_of_statuses():
    with pytest.raises(ValidationError):
        _statuses(*[{"name": f"Status {i}", "color": GREEN} for i in range(MAX_STATUSES + 1)])


def test_archived_statuses_do_not_count_for_the_limit():
    statuses = _statuses(
        *[{"name": f"Status {i}", "color": GREEN} for i in range(MAX_STATUSES)],
        {"name": "Old", "color": RED, "archived": True},
    )

    assert len(statuses.statuses) == MAX_STATUSES + 1
