import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from api.v2.routes.media import add_media, read_media
from results.error import (
    NotAuthorized, PointAlreadyHasMedia, StoreUnavailable, UnsupportedMediaType,
)
from settings import API_URL
from store.media_store import Media


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _file(filename: str | None = "photo.jpg", data=b"data"):
    return UploadFile(file=io.BytesIO(data), filename=filename)


def _media():
    return Media(id="media-1", point_id="p-1", storage_key="media-1.jpg", content_type="image/jpeg", size=4)


def _body(chunks=(b"da", b"ta")):
    body = MagicMock()
    body.iter_chunks.return_value = iter(chunks)
    return body


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.media.MediaStore.{method}", AsyncMock(**kwargs))


# ---- POST /v2/points/{point_id}/media ----

async def test_add_returns_the_media_with_its_v2_url():
    with _patch_store("add_media", return_value=_media()) as store:
        result = await add_media(point_id="p-1", file=_file(), user=_user())

    store.assert_awaited_once_with("p-1", "user-1", "photo.jpg", b"data")
    assert result.id == "media-1"
    assert result.url == f"{API_URL}/v2/media/media-1"
    assert result.content_type == "image/jpeg"
    assert result.size == 4


async def test_add_passes_an_empty_name_when_the_file_has_none():
    with _patch_store("add_media", return_value=_media()) as store:
        await add_media(point_id="p-1", file=_file(filename=None), user=_user())

    assert store.await_args.args[2] == ""


@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (UnsupportedMediaType(".exe"), 415),
    (PointAlreadyHasMedia("p-1"), 409),
    (StoreUnavailable(), 503),
])
async def test_add_maps_store_errors_to_http(error, status_code):
    with _patch_store("add_media", side_effect=error):
        with pytest.raises(HTTPException) as raised:
            await add_media(point_id="p-1", file=_file(), user=_user())

    assert raised.value.status_code == status_code


# ---- GET /v2/media/{media_id} ----

async def test_read_streams_the_media_bytes():
    body = _body()

    with _patch_store("read_media", return_value=(_media(), body)) as store:
        response = await read_media(media_id="media-1", user=_user())

    store.assert_awaited_once_with("media-1", "user-1")
    assert response.media_type == "image/jpeg"
    assert response.headers["content-length"] == "4"
    assert b"".join([chunk async for chunk in response.body_iterator]) == b"data"


async def test_read_closes_the_s3_stream_after_responding():
    body = _body()

    with _patch_store("read_media", return_value=(_media(), body)):
        response = await read_media(media_id="media-1", user=_user())
    await response.background()

    body.close.assert_called_once()


async def test_read_asks_as_anonymous_without_a_user():
    with _patch_store("read_media", return_value=(_media(), _body())) as store:
        await read_media(media_id="media-1", user=None)

    store.assert_awaited_once_with("media-1", None)


async def test_read_answers_not_found_when_the_media_is_missing_or_hidden():
    with _patch_store("read_media", return_value=None):
        with pytest.raises(HTTPException) as raised:
            await read_media(media_id="media-1", user=None)

    assert raised.value.status_code == 404


async def test_read_answers_unavailable_when_the_store_is_down():
    with _patch_store("read_media", side_effect=StoreUnavailable()):
        with pytest.raises(HTTPException) as raised:
            await read_media(media_id="media-1", user=_user())

    assert raised.value.status_code == 503
