from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.v2.routes.maps import read_map
from db import Map, SharePermission
from results.error import StoreUnavailable


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _map():
    return Map(
        id="map-1", name="A map", description="About it", owner_id="user-1",
        sharing=SharePermission.PUBLIC, is_live=True,
    )


def _point(point_id="p-1", status_id=None, status_updated_at=None, removed=False):
    return SimpleNamespace(
        id=point_id, message="a note", lat=1.0, lon=2.0, time=datetime(2026, 8, 21, 9, 48),
        file=None, removed=removed, tags="", status_id=status_id, status_updated_at=status_updated_at,
    )


def _status(status_id="s-1", name="Open", color="#3E9E47", description=""):
    return SimpleNamespace(id=status_id, name=name, color=color, description=description)


def _patch_stores(result, statuses=(), survey=None):
    return (
        patch("api.v2.routes.maps.MapsStore.read_map", AsyncMock(return_value=result)),
        patch("api.v2.routes.maps.MapStatusesStore.statuses_for", AsyncMock(return_value=list(statuses))),
        patch("api.v2.routes.maps.SurveyResponsesStore.responses_for_points", AsyncMock(return_value=survey or {})),
    )


async def _read(result, statuses=(), survey=None, user=None):
    maps, statuses_store, survey_store = _patch_stores(result, statuses, survey)
    with maps as read, statuses_store, survey_store as answers:
        response = await read_map(map_id="map-1", user=user)
    return response, read, answers


# ---- GET /v2/maps/{map_id} ----

async def test_read_returns_the_map_with_its_points():
    response, read, _ = await _read((_map(), True, [_point("p-1"), _point("p-2")]), user=_user())

    read.assert_awaited_once_with("map-1", "user-1")
    assert (response.id, response.name, response.description) == ("map-1", "A map", "About it")
    assert (response.sharing, response.owner, response.is_live) == ("public", True, True)
    assert response.type == "FeatureCollection"
    assert [feature.properties.id for feature in response.features] == ["p-1", "p-2"]
    assert response.features[0].geometry.coordinates == (2.0, 1.0)
    assert response.features[0].properties.message == "a note"


async def test_read_works_without_a_user():
    response, read, _ = await _read((_map(), False, []))

    read.assert_awaited_once_with("map-1", None)
    assert response.owner is False
    assert response.features == []


async def test_read_carries_the_statuses_of_the_map():
    statuses = [_status("s-1", "Open"), _status("s-2", "Closed", "#D73F3F", "Nobody can pass")]

    response, _, _ = await _read((_map(), True, []), statuses=statuses)

    assert [(status.id, status.name, status.color, status.description) for status in response.statuses] == [
        ("s-1", "Open", "#3E9E47", ""), ("s-2", "Closed", "#D73F3F", "Nobody can pass"),
    ]


async def test_read_carries_the_status_of_each_point():
    updated_at = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    points = [_point("p-1", status_id="s-1", status_updated_at=updated_at), _point("p-2")]

    response, _, _ = await _read((_map(), True, points), statuses=[_status("s-1")])

    first, second = [feature.properties for feature in response.features]
    assert (first.status, first.status_updated_at) == ("s-1", updated_at)
    assert (second.status, second.status_updated_at) == (None, None)


async def test_read_does_not_show_a_status_from_another_map():
    updated_at = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    points = [_point("p-1", status_id="s-9", status_updated_at=updated_at)]

    response, _, _ = await _read((_map(), True, points), statuses=[_status("s-1")])

    properties = response.features[0].properties
    assert (properties.status, properties.status_updated_at) == (None, None)


async def test_read_carries_the_survey_answers_of_each_point():
    survey = {"p-1": [{"question": "Smoothness", "answer": "intermediate"}]}

    response, _, answers = await _read((_map(), True, [_point("p-1"), _point("p-2")]), survey=survey)

    answers.assert_awaited_once_with(map_id="map-1", point_ids=["p-1", "p-2"])
    first, second = [feature.properties for feature in response.features]
    assert [(answer.question, answer.answer) for answer in first.survey] == [("Smoothness", "intermediate")]
    assert second.survey == []


async def test_read_does_not_find_a_map_the_user_cannot_see():
    with pytest.raises(HTTPException) as raised:
        await _read(None, user=_user())

    assert raised.value.status_code == 404


async def test_read_reports_the_store_as_unavailable():
    with patch("api.v2.routes.maps.MapsStore.read_map", AsyncMock(side_effect=StoreUnavailable())):
        with pytest.raises(HTTPException) as raised:
            await read_map(map_id="map-1", user=_user())

    assert raised.value.status_code == 503
