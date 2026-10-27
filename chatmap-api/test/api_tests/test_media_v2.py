import io
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient
from hotosm_auth_fastapi import get_current_user_optional

from api.v2 import router as v2_router
from api.v2.routes.media import add_media, list_map_media, media_uploader, read_media
from results.error import MapNotFound, NotAuthorized, PointAlreadyHasMedia, StoreUnavailable, UnsupportedMediaType
from settings import API_URL
from store.contributors.authorization import Owner
from store.credentials import Credentials
from store.media.model import Media

_CAPTURED_AT = datetime(2026, 10, 20, 15, 12, tzinfo=timezone(timedelta(hours=-3)))
_SECRET = "A" * 43
_AS_OWNER = Credentials(user_id="user-1", username="joaco")
_AS_CONTRIBUTOR = Credentials(contributor_secret=_SECRET)
_OWNER = Owner(user_id="user-1", username="joaco")
_CONTRIBUTOR = SimpleNamespace(id="c-1", removed_at=None)


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id, username="joaco")


def _file(filename: str | None = "photo.jpg", data=b"data"):
    return UploadFile(file=io.BytesIO(data), filename=filename)


def _media():
    return Media(id="media-1", point_id="p-1", storage_key="media-1.jpg", content_type="image/jpeg", size=4,
                 captured_at=datetime(2026, 10, 20, 18, 12))


def _body(chunks=(b"da", b"ta")):
    body = MagicMock()
    body.iter_chunks.return_value = iter(chunks)
    return body


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.media.MediaStore.{method}", AsyncMock(**kwargs))


def _client(user=None):
    app = FastAPI()
    app.include_router(v2_router)
    app.dependency_overrides[get_current_user_optional] = lambda: user
    return TestClient(app)


# ---- the uploader of a point ----

async def test_the_uploader_is_the_role_of_the_credentials_in_the_map_of_the_point():
    with _patch_store("uploader_of", return_value=_CONTRIBUTOR) as uploader_of:
        uploader = await media_uploader(point_id="p-1", credentials=_AS_CONTRIBUTOR)

    assert uploader is _CONTRIBUTOR
    uploader_of.assert_awaited_once_with("p-1", _AS_CONTRIBUTOR)


@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (StoreUnavailable(), 503),
])
async def test_the_uploader_maps_store_errors_to_http(error, status_code):
    with _patch_store("uploader_of", side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await media_uploader(point_id="p-1", credentials=_AS_CONTRIBUTOR)

    assert raised.value.status_code == status_code


# ---- POST /v2/points/{point_id}/media ----

async def test_add_returns_the_media_with_its_v2_url():
    with _patch_store("add_media", return_value=_media()) as store:
        result = await add_media(point_id="p-1", file=_file(), captured_at=_CAPTURED_AT, uploader=_OWNER)

    store.assert_awaited_once_with("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)
    assert result.id == "media-1"
    assert result.url == f"{API_URL}/v2/media/media-1"
    assert result.content_type == "image/jpeg"
    assert result.size == 4
    assert result.captured_at == datetime(2026, 10, 20, 18, 12, tzinfo=timezone.utc)


async def test_add_passes_an_empty_name_when_the_file_has_none():
    with _patch_store("add_media", return_value=_media()) as store:
        await add_media(point_id="p-1", file=_file(filename=None), captured_at=_CAPTURED_AT, uploader=_OWNER)

    assert store.await_args.args[2] == ""


async def test_add_passes_the_contributor_to_the_store():
    with _patch_store("add_media", return_value=_media()) as store:
        await add_media(point_id="p-1", file=_file(), captured_at=_CAPTURED_AT, uploader=_CONTRIBUTOR)

    store.assert_awaited_once_with("p-1", _CONTRIBUTOR, "photo.jpg", b"data", _CAPTURED_AT)


@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (UnsupportedMediaType(".exe"), 415),
    (PointAlreadyHasMedia("p-1"), 409),
    (StoreUnavailable(), 503),
])
async def test_add_maps_store_errors_to_http(error, status_code):
    with _patch_store("add_media", side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await add_media(point_id="p-1", file=_file(), captured_at=_CAPTURED_AT, uploader=_CONTRIBUTOR)

    assert raised.value.status_code == status_code


# ---- GET /v2/media/{media_id} ----

async def test_read_streams_the_media_bytes():
    body = _body()

    with _patch_store("read_media", return_value=(_media(), body)) as store:
        response = await read_media(media_id="media-1", credentials=_AS_OWNER)

    store.assert_awaited_once_with("media-1", _AS_OWNER)
    assert response.media_type == "image/jpeg"
    assert response.headers["content-length"] == "4"
    assert b"".join([chunk async for chunk in response.body_iterator]) == b"data"


async def test_read_closes_the_s3_stream_after_responding():
    body = _body()

    with _patch_store("read_media", return_value=(_media(), body)):
        response = await read_media(media_id="media-1", credentials=_AS_OWNER)
    await response.background()

    body.close.assert_called_once()


async def test_read_asks_as_anonymous_without_credentials():
    with _patch_store("read_media", return_value=(_media(), _body())) as store:
        await read_media(media_id="media-1", credentials=Credentials())

    store.assert_awaited_once_with("media-1", Credentials())


async def test_read_passes_the_contributor_credentials_to_the_store():
    with _patch_store("read_media", return_value=(_media(), _body())) as store:
        await read_media(media_id="media-1", credentials=_AS_CONTRIBUTOR)

    store.assert_awaited_once_with("media-1", _AS_CONTRIBUTOR)


async def test_read_answers_not_found_when_the_media_is_missing_or_hidden():
    with _patch_store("read_media", return_value=None):
        with pytest.raises(HTTPException) as raised:
            await read_media(media_id="media-1", credentials=Credentials())

    assert raised.value.status_code == 404


async def test_read_answers_unavailable_when_the_store_is_down():
    with _patch_store("read_media", side_effect=StoreUnavailable()):
        with pytest.raises(HTTPException) as raised:
            await read_media(media_id="media-1", credentials=_AS_OWNER)

    assert raised.value.status_code == 503


# ---- GET /v2/maps/{map_id}/media ----

async def test_list_returns_the_media_of_the_map_with_their_points():
    with _patch_store("media_of_map", return_value=[_media()]) as store:
        result = await list_map_media(map_id="map-1", credentials=_AS_OWNER)

    store.assert_awaited_once_with("map-1", _AS_OWNER)
    [item] = result.media
    assert item.point_id == "p-1"
    assert item.id == "media-1"
    assert item.url == f"{API_URL}/v2/media/media-1"
    assert item.content_type == "image/jpeg"
    assert item.captured_at == datetime(2026, 10, 20, 18, 12, tzinfo=timezone.utc)


async def test_list_of_a_map_without_media_is_empty():
    with _patch_store("media_of_map", return_value=[]):
        result = await list_map_media(map_id="map-1", credentials=_AS_OWNER)

    assert result.media == []


async def test_list_asks_as_anonymous_without_credentials():
    with _patch_store("media_of_map", return_value=[]) as store:
        await list_map_media(map_id="map-1", credentials=Credentials())

    store.assert_awaited_once_with("map-1", Credentials())


@pytest.mark.parametrize("error, status_code", [
    (MapNotFound(), 404),
    (NotAuthorized(), 403),
    (StoreUnavailable(), 503),
])
async def test_list_maps_store_errors_to_http(error, status_code):
    with _patch_store("media_of_map", side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await list_map_media(map_id="map-1", credentials=_AS_OWNER)

    assert raised.value.status_code == status_code


# ---- over HTTP ----

_UPLOAD = {"file": ("photo.jpg", b"data", "image/jpeg")}
_FORM = {"captured_at": "2026-10-20T15:12:00-03:00"}


def test_http_upload_without_credentials_answers_unauthorized_before_looking_at_the_file():
    response = _client().post("/v2/points/p-1/media")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_http_upload_with_a_malformed_contributor_secret_answers_unauthorized():
    response = _client().post("/v2/points/p-1/media", files=_UPLOAD, headers={"Authorization": "Contributor nope"})

    assert response.status_code == 401


def test_http_upload_as_a_contributor_attaches_the_media():
    with _patch_store("uploader_of", return_value=_CONTRIBUTOR) as uploader_of, \
            _patch_store("add_media", return_value=_media()) as store:
        response = _client().post(
            "/v2/points/p-1/media", files=_UPLOAD, data=_FORM, headers={"Authorization": f"Contributor {_SECRET}"},
        )

    assert response.status_code == 201
    assert response.json()["url"] == f"{API_URL}/v2/media/media-1"
    assert response.json()["captured_at"] == "2026-10-20T18:12:00Z"
    uploader_of.assert_awaited_once_with("p-1", _AS_CONTRIBUTOR)
    store.assert_awaited_once_with("p-1", _CONTRIBUTOR, "photo.jpg", b"data", _CAPTURED_AT)


def test_http_upload_as_the_owner_attaches_the_media():
    with _patch_store("uploader_of", return_value=_OWNER) as uploader_of, \
            _patch_store("add_media", return_value=_media()) as store:
        response = _client(user=_user()).post("/v2/points/p-1/media", files=_UPLOAD, data=_FORM)

    assert response.status_code == 201
    uploader_of.assert_awaited_once_with("p-1", _AS_OWNER)
    store.assert_awaited_once_with("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)


def test_http_upload_answers_forbidden_when_there_is_no_uploader():
    with _patch_store("uploader_of", side_effect=NotAuthorized()), _patch_store("add_media") as store:
        response = _client().post(
            "/v2/points/p-1/media", files=_UPLOAD, data=_FORM, headers={"Authorization": f"Contributor {_SECRET}"},
        )

    assert response.status_code == 403
    store.assert_not_awaited()


@pytest.mark.parametrize("form", [
    {},
    {"captured_at": "2026-10-20T15:12:00"},
    {"captured_at": "not a time"},
])
def test_http_upload_without_a_capture_time_with_its_zone_answers_unprocessable(form):
    with _patch_store("uploader_of", return_value=_CONTRIBUTOR), \
            _patch_store("add_media", return_value=_media()) as store:
        response = _client().post(
            "/v2/points/p-1/media", files=_UPLOAD, data=form, headers={"Authorization": f"Contributor {_SECRET}"},
        )

    assert response.status_code == 422
    store.assert_not_awaited()


def test_http_read_without_credentials_still_reaches_the_store_for_public_maps():
    with _patch_store("read_media", return_value=None) as store:
        response = _client().get("/v2/media/media-1")

    assert response.status_code == 404
    store.assert_awaited_once_with("media-1", Credentials())


def test_http_read_as_a_contributor_streams_the_media():
    with _patch_store("read_media", return_value=(_media(), _body())) as store:
        response = _client().get("/v2/media/media-1", headers={"Authorization": f"Contributor {_SECRET}"})

    assert response.status_code == 200
    assert response.content == b"data"
    assert response.headers["content-type"] == "image/jpeg"
    store.assert_awaited_once_with("media-1", _AS_CONTRIBUTOR)


def test_http_list_without_credentials_still_reaches_the_store_for_public_maps():
    with _patch_store("media_of_map", return_value=[_media()]) as store:
        response = _client().get("/v2/maps/map-1/media")

    assert response.status_code == 200
    assert response.json()["media"][0]["point_id"] == "p-1"
    store.assert_awaited_once_with("map-1", Credentials())


def test_http_list_as_the_owner_passes_the_session():
    with _patch_store("media_of_map", return_value=[]) as store:
        response = _client(user=_user()).get("/v2/maps/map-1/media")

    assert response.status_code == 200
    assert response.json() == {"media": []}
    store.assert_awaited_once_with("map-1", _AS_OWNER)
