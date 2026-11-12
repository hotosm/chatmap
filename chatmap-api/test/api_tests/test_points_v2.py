from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from hotosm_auth_fastapi import get_current_user_optional
from pydantic import ValidationError

from api.v2 import router as v2_router
from api.v2.routes.points import create_point, history_contributor, list_points, point_author
from api.v2.schemas.point import CreatePointRequest
from results.error import InvalidCursor, MapNotFound, NotAuthorized, StoreUnavailable
from settings import API_URL
from store.contributors.authorization import Owner
from store.credentials import Credentials
from store.points.store import HistoryMedia, HistoryPage, HistoryPoint, PointCreation

_ID = "a" * 64
_SECRET = "A" * 43
_TIME = datetime(2026, 10, 7, 12, 15, 23, tzinfo=timezone(timedelta(hours=-3)))
_AS_OWNER = Credentials(user_id="user-1", username="joaco")
_AS_CONTRIBUTOR = Credentials(contributor_secret=_SECRET)
_OWNER = Owner(user_id="user-1", username="joaco")
_CONTRIBUTOR = SimpleNamespace(id="c-1", nickname="Ana", removed_at=None)


def _user(user_id="user-1", username="joaco"):
    return SimpleNamespace(id=user_id, username=username)


def _body(**overrides):
    return {
        "map_id": "map-1",
        "latitude": -34.6,
        "longitude": -58.38,
        "time": "2026-10-07T12:15:23-03:00",
        "message": "Calle inundada",
        **overrides,
    }


def _request(**overrides):
    return CreatePointRequest.model_validate(_body(**overrides))


def _creation(created=True):
    return PointCreation(id=_ID, created=created)


def _patch_store(**kwargs):
    return patch("api.v2.routes.points.PointStore.create_point", AsyncMock(**kwargs))


def _patch_role(**kwargs):
    return patch("api.v2.routes.points.MapStore.role_of", AsyncMock(**kwargs))


def _client(user=None):
    app = FastAPI()
    app.include_router(v2_router)
    app.dependency_overrides[get_current_user_optional] = lambda: user
    return TestClient(app)


# ---- the author of a point ----

async def test_the_author_is_the_role_of_the_credentials_in_the_map_of_the_point():
    with _patch_role(return_value=_CONTRIBUTOR) as role_of:
        author = await point_author(point=_request(), credentials=_AS_CONTRIBUTOR)

    assert author is _CONTRIBUTOR
    role_of.assert_awaited_once_with("map-1", _AS_CONTRIBUTOR)


@pytest.mark.parametrize("error, status_code", [
    (MapNotFound(), 404),
    (NotAuthorized(), 403),
    (StoreUnavailable(), 503),
])
async def test_the_author_maps_store_errors_to_http(error, status_code):
    with _patch_role(side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await point_author(point=_request(), credentials=_AS_CONTRIBUTOR)

    assert raised.value.status_code == status_code


# ---- POST /v2/points ----

async def test_create_answers_created_with_the_point_id():
    response = Response()

    with _patch_store(return_value=_creation(created=True)):
        result = await create_point(point=_request(), response=response, author=_OWNER)

    assert response.status_code == 201
    assert result.id == _ID


async def test_create_answers_ok_when_the_point_already_existed():
    response = Response()

    with _patch_store(return_value=_creation(created=False)):
        result = await create_point(point=_request(), response=response, author=_OWNER)

    assert response.status_code == 200
    assert result.id == _ID


@pytest.mark.parametrize("author", [_OWNER, _CONTRIBUTOR])
async def test_create_passes_the_point_and_the_author_to_the_store(author):
    with _patch_store(return_value=_creation()) as store:
        await create_point(point=_request(), response=Response(), author=author)

    store.assert_awaited_once_with(
        map_id="map-1",
        author=author,
        latitude=-34.6,
        longitude=-58.38,
        time=_TIME,
        message="Calle inundada",
    )


async def test_create_ignores_an_id_sent_by_the_client():
    with _patch_store(return_value=_creation()) as store:
        await create_point(point=_request(id="client-chosen"), response=Response(), author=_OWNER)

    assert "id" not in store.await_args.kwargs
    assert "point_id" not in store.await_args.kwargs


async def test_create_answers_unavailable_when_the_store_fails():
    with _patch_store(side_effect=StoreUnavailable()):
        with pytest.raises(HTTPException) as raised:
            await create_point(point=_request(), response=Response(), author=_CONTRIBUTOR)

    assert raised.value.status_code == 503


# ---- POST /v2/points over HTTP ----

def test_http_without_credentials_answers_unauthorized_before_validating_the_body():
    response = _client().post("/v2/points", json={})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_http_with_a_malformed_contributor_secret_answers_unauthorized():
    response = _client().post(
        "/v2/points", json=_body(), headers={"Authorization": "Contributor not-a-secret"},
    )

    assert response.status_code == 401


def test_http_with_a_contributor_secret_creates_the_point_as_that_contributor():
    with _patch_role(return_value=_CONTRIBUTOR) as role_of, _patch_store(return_value=_creation()) as store:
        response = _client().post(
            "/v2/points", json=_body(), headers={"Authorization": f"Contributor {_SECRET}"},
        )

    assert response.status_code == 201
    assert response.json() == {"id": _ID}
    role_of.assert_awaited_once_with("map-1", _AS_CONTRIBUTOR)
    assert store.await_args.kwargs["author"] is _CONTRIBUTOR


def test_http_with_a_session_creates_the_point_as_the_owner():
    with _patch_role(return_value=_OWNER) as role_of, _patch_store(return_value=_creation(created=False)) as store:
        response = _client(user=_user()).post("/v2/points", json=_body())

    assert response.status_code == 200
    assert response.json() == {"id": _ID}
    role_of.assert_awaited_once_with("map-1", _AS_OWNER)
    assert store.await_args.kwargs["author"] == _OWNER


def test_http_with_a_session_and_a_secret_uses_only_the_secret():
    with _patch_role(return_value=_CONTRIBUTOR) as role_of, _patch_store(return_value=_creation()):
        _client(user=_user()).post("/v2/points", json=_body(), headers={"Authorization": f"Contributor {_SECRET}"})

    role_of.assert_awaited_once_with("map-1", _AS_CONTRIBUTOR)


def test_http_answers_not_found_for_a_map_that_is_not_the_session_owner():
    with _patch_role(side_effect=MapNotFound()), _patch_store(return_value=_creation()) as store:
        response = _client(user=_user()).post("/v2/points", json=_body())

    assert response.status_code == 404
    store.assert_not_awaited()


def test_http_validates_the_body_before_looking_for_the_author():
    with _patch_role(return_value=_CONTRIBUTOR) as role_of:
        response = _client().post(
            "/v2/points", json=_body(latitude=100), headers={"Authorization": f"Contributor {_SECRET}"},
        )

    assert response.status_code == 422
    role_of.assert_not_awaited()


# ---- the contributor of a history ----

def _patch_active(**kwargs):
    return patch("api.v2.routes.points.ContributorStore.active_in", AsyncMock(**kwargs))


async def test_the_history_contributor_is_the_active_contributor_of_the_secret_in_the_map():
    with _patch_active(return_value=_CONTRIBUTOR) as active_in:
        contributor = await history_contributor(map_id="map-1", credentials=_AS_CONTRIBUTOR)

    assert contributor is _CONTRIBUTOR
    active_in.assert_awaited_once_with("map-1", _AS_CONTRIBUTOR)


@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (StoreUnavailable(), 503),
])
async def test_the_history_contributor_maps_store_errors_to_http(error, status_code):
    with _patch_active(side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await history_contributor(map_id="map-1", credentials=_AS_CONTRIBUTOR)

    assert raised.value.status_code == status_code


# ---- GET /v2/maps/{map_id}/points ----

def _patch_history(**kwargs):
    return patch("api.v2.routes.points.PointStore.contributor_points", AsyncMock(**kwargs))


def _history_point(point_id="p-1", media=None):
    return HistoryPoint(
        id=point_id,
        time=datetime(2026, 10, 20, 14, 3, 11, tzinfo=timezone.utc),
        latitude=-34.6037,
        longitude=-58.3816,
        message="Esquina con la escuela",
        media=media,
    )


async def test_list_points_returns_each_point_with_its_media_link():
    media = HistoryMedia(
        id="m-1",
        content_type="image/jpeg",
        size=482113,
        captured_at=datetime(2026, 10, 20, 14, 5, 40, tzinfo=timezone.utc),
    )
    page = HistoryPage(points=[_history_point("p-1", media), _history_point("p-2")], next="abc")

    with _patch_history(return_value=page):
        result = await list_points(map_id="map-1", contributor=_CONTRIBUTOR, cursor=None)

    assert result.model_dump(mode="json") == {
        "points": [
            {
                "id": "p-1",
                "time": "2026-10-20T14:03:11Z",
                "latitude": -34.6037,
                "longitude": -58.3816,
                "message": "Esquina con la escuela",
                "media": {
                    "id": "m-1",
                    "url": f"{API_URL}/v2/media/m-1",
                    "content_type": "image/jpeg",
                    "size": 482113,
                    "captured_at": "2026-10-20T14:05:40Z",
                },
            },
            {
                "id": "p-2",
                "time": "2026-10-20T14:03:11Z",
                "latitude": -34.6037,
                "longitude": -58.3816,
                "message": "Esquina con la escuela",
                "media": None,
            },
        ],
        "next": "abc",
    }


async def test_list_points_asks_the_store_with_the_map_the_contributor_and_the_cursor():
    with _patch_history(return_value=HistoryPage(points=[], next=None)) as store:
        await list_points(map_id="map-1", contributor=_CONTRIBUTOR, cursor="abc")

    store.assert_awaited_once_with("map-1", _CONTRIBUTOR, "abc")


@pytest.mark.parametrize("error, status_code", [
    (InvalidCursor(), 422),
    (StoreUnavailable(), 503),
])
async def test_list_points_maps_store_errors_to_http(error, status_code):
    with _patch_history(side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await list_points(map_id="map-1", contributor=_CONTRIBUTOR, cursor=None)

    assert raised.value.status_code == status_code


def test_http_list_points_with_a_contributor_secret_returns_the_page():
    page = HistoryPage(points=[_history_point()], next=None)

    with _patch_active(return_value=_CONTRIBUTOR) as active_in, _patch_history(return_value=page) as store:
        response = _client().get(
            "/v2/maps/map-1/points?cursor=abc", headers={"Authorization": f"Contributor {_SECRET}"},
        )

    assert response.status_code == 200
    assert response.json()["points"][0]["time"] == "2026-10-20T14:03:11Z"
    assert response.json()["next"] is None
    active_in.assert_awaited_once_with("map-1", _AS_CONTRIBUTOR)
    store.assert_awaited_once_with("map-1", _CONTRIBUTOR, "abc")


def test_http_list_points_without_a_cursor_asks_for_the_first_page():
    with _patch_active(return_value=_CONTRIBUTOR), \
            _patch_history(return_value=HistoryPage(points=[], next=None)) as store:
        _client().get("/v2/maps/map-1/points", headers={"Authorization": f"Contributor {_SECRET}"})

    store.assert_awaited_once_with("map-1", _CONTRIBUTOR, None)


def test_http_list_points_answers_forbidden_to_a_secret_that_is_not_an_active_contributor():
    with _patch_active(side_effect=NotAuthorized()), _patch_history() as store:
        response = _client().get("/v2/maps/map-1/points", headers={"Authorization": f"Contributor {_SECRET}"})

    assert response.status_code == 403
    store.assert_not_awaited()


def test_http_list_points_without_credentials_answers_unauthorized():
    response = _client().get("/v2/maps/map-1/points")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Contributor"


def test_http_list_points_with_only_a_session_answers_unauthorized():
    response = _client(user=_user()).get("/v2/maps/map-1/points")

    assert response.status_code == 401


# ---- CreatePointRequest ----

def test_request_leaves_the_message_empty_when_missing():
    body = _body()
    del body["message"]

    assert CreatePointRequest.model_validate(body).message is None


def test_request_ignores_unknown_fields():
    request = _request(id="x", username="someone", file="photo.jpg", tags="flood")

    assert set(request.model_dump()) == {"map_id", "latitude", "longitude", "time", "message"}


@pytest.mark.parametrize("field", ["map_id", "latitude", "longitude", "time"])
def test_request_requires_the_field(field):
    body = _body()
    del body[field]

    with pytest.raises(ValidationError):
        CreatePointRequest.model_validate(body)


@pytest.mark.parametrize("overrides", [
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
