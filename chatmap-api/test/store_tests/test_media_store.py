from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from db import Map, SharePermission
from results.error import (
    NotAuthorized, PointAlreadyHasMedia, StoreUnavailable, UnsupportedMediaType,
)
from store.media_store import Media, MediaStore


@pytest.fixture
def s3():
    with patch("store.media_store._put_object", AsyncMock()) as put, \
            patch("store.media_store._get_object", AsyncMock(return_value="body")) as get, \
            patch("store.media_store._discard_object", AsyncMock()) as discard:
        yield SimpleNamespace(put=put, get=get, discard=discard)


def _db_row(row):
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = row
    return db


def _patch_scope(*dbs):
    scope = MagicMock()
    scope.return_value.__enter__.side_effect = list(dbs)
    scope.return_value.__exit__.return_value = False
    return patch("store.media_store.session_scope", scope)


def _point(owner_id="user-1", media_id=None):
    return SimpleNamespace(owner_id=owner_id, id=media_id)


def _media():
    return Media(id="media-1", point_id="p-1", storage_key="media-1.jpg", content_type="image/jpeg", size=4)


def _map(sharing=SharePermission.PRIVATE, owner_id="user-1"):
    return Map(id="map-1", sharing=sharing, owner_id=owner_id)


def _s3_error():
    return ClientError({"Error": {"Code": "500", "Message": "boom"}}, "S3")


# ---- add_media ----

async def test_add_rejects_a_point_that_does_not_exist(s3):
    with _patch_scope(_db_row(None)):
        with pytest.raises(NotAuthorized):
            await MediaStore.add_media("p-1", "user-1", "photo.jpg", b"data")

    s3.put.assert_not_awaited()


async def test_add_rejects_a_user_who_cannot_contribute_to_the_map(s3):
    with _patch_scope(_db_row(_point(owner_id="someone-else"))):
        with pytest.raises(NotAuthorized):
            await MediaStore.add_media("p-1", "user-1", "photo.jpg", b"data")

    s3.put.assert_not_awaited()


async def test_add_checks_authorization_before_the_file_type(s3):
    with _patch_scope(_db_row(_point(owner_id="someone-else"))):
        with pytest.raises(NotAuthorized):
            await MediaStore.add_media("p-1", "user-1", "malware.exe", b"data")


async def test_add_rejects_an_unsupported_file_type(s3):
    with _patch_scope(_db_row(_point())):
        with pytest.raises(UnsupportedMediaType):
            await MediaStore.add_media("p-1", "user-1", "malware.exe", b"data")

    s3.put.assert_not_awaited()


async def test_add_rejects_a_point_that_already_has_media(s3):
    with _patch_scope(_db_row(_point(media_id="media-1"))):
        with pytest.raises(PointAlreadyHasMedia):
            await MediaStore.add_media("p-1", "user-1", "photo.jpg", b"data")

    s3.put.assert_not_awaited()


async def test_add_uploads_the_file_and_saves_the_media(s3):
    save_db = MagicMock()

    with _patch_scope(_db_row(_point()), save_db):
        media = await MediaStore.add_media("p-1", "user-1", "Photo.JPG", b"data")

    assert media.point_id == "p-1"
    assert media.storage_key == f"{media.id}.jpg"
    assert media.content_type == "image/jpeg"
    assert media.size == 4
    s3.put.assert_awaited_once_with(media.storage_key, b"data", "image/jpeg")
    save_db.add.assert_called_once_with(media)
    save_db.commit.assert_called_once()


async def test_add_saves_nothing_when_the_upload_fails(s3):
    s3.put.side_effect = _s3_error()
    save_db = MagicMock()

    with _patch_scope(_db_row(_point()), save_db):
        with pytest.raises(StoreUnavailable):
            await MediaStore.add_media("p-1", "user-1", "photo.jpg", b"data")

    save_db.add.assert_not_called()


async def test_add_loses_a_race_for_the_same_point(s3):
    save_db = MagicMock()
    save_db.commit.side_effect = IntegrityError("INSERT", {}, UniqueViolation())

    with _patch_scope(_db_row(_point()), save_db):
        with pytest.raises(PointAlreadyHasMedia):
            await MediaStore.add_media("p-1", "user-1", "photo.jpg", b"data")

    s3.discard.assert_awaited_once_with(s3.put.await_args.args[0])


@pytest.mark.parametrize("error", [
    IntegrityError("INSERT", {}, ForeignKeyViolation()),
    SQLAlchemyError("boom"),
])
async def test_add_discards_the_upload_when_saving_fails(s3, error):
    save_db = MagicMock()
    save_db.commit.side_effect = error

    with _patch_scope(_db_row(_point()), save_db):
        with pytest.raises(StoreUnavailable):
            await MediaStore.add_media("p-1", "user-1", "photo.jpg", b"data")

    s3.discard.assert_awaited_once_with(s3.put.await_args.args[0])


# ---- read_media ----

async def test_read_returns_nothing_for_a_missing_media(s3):
    with _patch_scope(_db_row(None)):
        assert await MediaStore.read_media("media-1", "user-1") is None

    s3.get.assert_not_awaited()


@pytest.mark.parametrize("user_id", ["someone-else", None])
async def test_read_hides_media_of_a_private_map_from_non_owners(s3, user_id):
    with _patch_scope(_db_row((_media(), _map()))):
        assert await MediaStore.read_media("media-1", user_id) is None

    s3.get.assert_not_awaited()


async def test_read_shows_media_of_a_private_map_to_its_owner(s3):
    media = _media()

    with _patch_scope(_db_row((media, _map()))):
        result = await MediaStore.read_media("media-1", "user-1")

    assert result == (media, "body")
    s3.get.assert_awaited_once_with("media-1.jpg")


async def test_read_shows_media_of_a_public_map_to_anyone(s3):
    media = _media()

    with _patch_scope(_db_row((media, _map(sharing=SharePermission.PUBLIC)))):
        result = await MediaStore.read_media("media-1", None)

    assert result == (media, "body")


async def test_read_raises_store_unavailable_when_s3_fails(s3):
    s3.get.side_effect = _s3_error()

    with _patch_scope(_db_row((_media(), _map()))):
        with pytest.raises(StoreUnavailable):
            await MediaStore.read_media("media-1", "user-1")
