from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from api.v2.routes.points import create_point
from api.v2.schemas.point import CreatePointRequest
from results.error import MapNotFound, PointIdAlreadyTaken, StoreUnavailable

_ID = "3f1c2b9e-8a4d-4c1e-9f6a-2d7b5e0c1a84"


def _user(user_id="user-1", username="joaco"):
    return SimpleNamespace(id=user_id, username=username)


def _body(**overrides):
    return {
        "id": _ID,
        "map_id": "map-1",
        "latitude": -34.6,
        "longitude": -58.38,
        "time": "2026-10-07T12:15:23-03:00",
        "message": "Calle inundada",
        **overrides,
    }


def _request(**overrides):
    return CreatePointRequest.model_validate(_body(**overrides))


def _patch_store(**kwargs):
    return patch("api.v2.routes.points.PointStore.create_point", AsyncMock(**kwargs))


# ---- POST /v2/points ----

async def test_create_answers_created_with_the_point_id():
    response = Response()

    with _patch_store(return_value=True):
        result = await create_point(point=_request(), response=response, user=_user())

    assert response.status_code == 201
    assert result.id == _ID


async def test_create_answers_ok_when_the_point_already_existed():
    response = Response()

    with _patch_store(return_value=False):
        result = await create_point(point=_request(), response=response, user=_user())

    assert response.status_code == 200
    assert result.id == _ID


async def test_create_passes_the_point_and_the_hanko_username_to_the_store():
    with _patch_store(return_value=True) as store:
        await create_point(point=_request(), response=Response(), user=_user())

    store.assert_awaited_once_with(
        point_id=_ID,
        map_id="map-1",
        user_id="user-1",
        username="joaco",
        latitude=-34.6,
        longitude=-58.38,
        time=datetime(2026, 10, 7, 12, 15, 23, tzinfo=timezone(timedelta(hours=-3))),
        message="Calle inundada",
    )


async def test_create_passes_no_username_when_the_user_has_none():
    with _patch_store(return_value=True) as store:
        await create_point(point=_request(), response=Response(), user=_user(username=None))

    assert store.await_args.kwargs["username"] is None


async def test_create_uses_the_id_in_canonical_form():
    with _patch_store(return_value=True) as store:
        result = await create_point(point=_request(id=_ID.upper()), response=Response(), user=_user())

    assert store.await_args.kwargs["point_id"] == _ID
    assert result.id == _ID


@pytest.mark.parametrize("error, status_code", [
    (MapNotFound(), 404),
    (PointIdAlreadyTaken(_ID), 409),
    (StoreUnavailable(), 503),
])
async def test_create_maps_store_errors_to_http(error, status_code):
    with _patch_store(side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await create_point(point=_request(), response=Response(), user=_user())

    assert raised.value.status_code == status_code


# ---- CreatePointRequest ----

def test_request_leaves_the_message_empty_when_missing():
    body = _body()
    del body["message"]

    assert CreatePointRequest.model_validate(body).message is None


def test_request_ignores_unknown_fields():
    request = _request(username="someone", file="photo.jpg", tags="flood")

    assert set(request.model_dump()) == {"id", "map_id", "latitude", "longitude", "time", "message"}


@pytest.mark.parametrize("field", ["id", "map_id", "latitude", "longitude", "time"])
def test_request_requires_the_field(field):
    body = _body()
    del body[field]

    with pytest.raises(ValidationError):
        CreatePointRequest.model_validate(body)


@pytest.mark.parametrize("overrides", [
    {"id": "1759850123000-0"},
    {"latitude": 90.1},
    {"latitude": -90.1},
    {"latitude": float("nan")},
    {"longitude": 180.1},
    {"longitude": -180.1},
    {"time": "2026-10-07T12:15:23"},
])
def test_request_rejects_an_invalid_field(overrides):
    with pytest.raises(ValidationError):
        _request(**overrides)
