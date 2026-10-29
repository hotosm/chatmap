from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import hashlib

import pytest
from botocore.exceptions import ClientError
from psycopg2.errors import ForeignKeyViolation, UniqueViolation
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from db import Map, SharePermission
from results.error import MapNotFound, NotAuthorized, PointAlreadyHasMedia, StoreUnavailable, UnsupportedMediaType
from store.contributors.authorization import Owner
from store.credentials import Credentials
from store.media.model import Media
from store.media.store import MediaStore

_CAPTURED_AT = datetime(2026, 10, 20, 15, 12, tzinfo=timezone(timedelta(hours=-3)))
_SECRET = "s" * 43
_OWNER = Owner(user_id="user-1", username="joaco")
_AS_OWNER = Credentials(user_id="user-1", username="joaco")
_AS_CONTRIBUTOR = Credentials(contributor_secret=_SECRET)


@pytest.fixture
def s3():
    with patch("store.media.store.put_object", AsyncMock()) as put, \
            patch("store.media.store.get_object", AsyncMock(return_value="body")) as get, \
            patch("store.media.store.discard_object", AsyncMock()) as discard:
        yield SimpleNamespace(put=put, get=get, discard=discard)


def _db_row(row):
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = row
    return db


def _patch_scope(*dbs):
    scope = MagicMock()
    scope.return_value.__enter__.side_effect = list(dbs)
    scope.return_value.__exit__.return_value = False
    return patch("store.media.store.session_scope", scope)


def _point(owner_id="user-1", media_id=None, map_id="map-1", contributor_id=None):
    return SimpleNamespace(owner_id=owner_id, id=media_id, map_id=map_id, contributor_id=contributor_id)


def _contributor(contributor_id="c-1", removed_at=None):
    return SimpleNamespace(id=contributor_id, removed_at=removed_at)


def _db_with_contributor(row, contributor):
    db = _db_row(row)
    db.execute.return_value.scalar_one_or_none.return_value = contributor
    return db


def _media():
    return Media(id="media-1", point_id="p-1", storage_key="media-1.jpg", content_type="image/jpeg", size=4)


def _map(sharing=SharePermission.PRIVATE, owner_id="user-1"):
    return Map(id="map-1", sharing=sharing, owner_id=owner_id)


def _s3_error():
    return ClientError({"Error": {"Code": "500", "Message": "boom"}}, "S3")


# ---- uploader_of ----

async def test_uploader_of_rejects_a_point_that_does_not_exist():
    db = _db_row(None)

    with _patch_scope(db):
        with pytest.raises(NotAuthorized):
            await MediaStore.uploader_of("p-1", _AS_OWNER)

    assert db.execute.call_count == 1


async def test_uploader_of_the_owner_of_the_map_is_the_owner():
    with _patch_scope(_db_row(_point(owner_id="user-1"))):
        assert await MediaStore.uploader_of("p-1", _AS_OWNER) == _OWNER


async def test_uploader_of_rejects_a_session_that_does_not_own_the_map():
    with _patch_scope(_db_row(_point(owner_id="someone-else"))):
        with pytest.raises(NotAuthorized):
            await MediaStore.uploader_of("p-1", _AS_OWNER)


async def test_uploader_of_an_active_contributor_is_that_contributor():
    contributor = _contributor("c-1")

    with _patch_scope(_db_with_contributor(_point(contributor_id="c-1"), contributor)):
        assert await MediaStore.uploader_of("p-1", _AS_CONTRIBUTOR) is contributor


@pytest.mark.parametrize("contributor", [None, _contributor(removed_at="2026-10-01")])
async def test_uploader_of_rejects_a_secret_without_an_active_contributor(contributor):
    with _patch_scope(_db_with_contributor(_point(), contributor)):
        with pytest.raises(NotAuthorized):
            await MediaStore.uploader_of("p-1", _AS_CONTRIBUTOR)


async def test_uploader_of_looks_the_contributor_up_in_the_map_of_the_point_by_the_hash_of_the_secret():
    db = _db_with_contributor(_point(map_id="map-7"), _contributor("c-1"))

    with _patch_scope(db):
        await MediaStore.uploader_of("p-1", _AS_CONTRIBUTOR)

    params = db.execute.call_args_list[1].args[0].compile(dialect=postgresql.dialect()).params
    assert "map-7" in params.values()
    assert hashlib.sha256(_SECRET.encode()).hexdigest() in params.values()
    assert _SECRET not in params.values()


async def test_uploader_of_reports_the_store_unavailable_when_the_lookup_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await MediaStore.uploader_of("p-1", _AS_CONTRIBUTOR)


# ---- add_media as the owner ----

async def test_add_rejects_a_point_that_does_not_exist(s3):
    with _patch_scope(_db_row(None)):
        with pytest.raises(NotAuthorized):
            await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

    s3.put.assert_not_awaited()


async def test_add_lets_the_owner_attach_to_a_point_of_a_contributor(s3):
    with _patch_scope(_db_row(_point(contributor_id="c-9")), MagicMock()):
        media = await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

    assert media.point_id == "p-1"


async def test_add_rejects_an_unsupported_file_type(s3):
    with _patch_scope(_db_row(_point())):
        with pytest.raises(UnsupportedMediaType):
            await MediaStore.add_media("p-1", _OWNER, "malware.exe", b"data", _CAPTURED_AT)

    s3.put.assert_not_awaited()


async def test_add_rejects_a_point_that_already_has_media(s3):
    with _patch_scope(_db_row(_point(media_id="media-1"))):
        with pytest.raises(PointAlreadyHasMedia):
            await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

    s3.put.assert_not_awaited()


async def test_add_uploads_the_file_and_saves_the_media(s3):
    save_db = MagicMock()

    with _patch_scope(_db_row(_point()), save_db):
        media = await MediaStore.add_media("p-1", _OWNER, "Photo.JPG", b"data", _CAPTURED_AT)

    assert media.point_id == "p-1"
    assert media.storage_key == f"{media.id}.jpg"
    assert media.content_type == "image/jpeg"
    assert media.size == 4
    s3.put.assert_awaited_once_with(media.storage_key, b"data", "image/jpeg")
    save_db.add.assert_called_once_with(media)
    save_db.commit.assert_called_once()


async def test_add_accepts_a_video_recorded_on_ios(s3):
    with _patch_scope(_db_row(_point()), MagicMock()):
        media = await MediaStore.add_media("p-1", _OWNER, "clip.mov", b"data", _CAPTURED_AT)

    assert media.storage_key == f"{media.id}.mov"
    assert media.content_type == "video/quicktime"


async def test_add_saves_the_capture_time_in_utc(s3):
    with _patch_scope(_db_row(_point()), MagicMock()):
        media = await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

    assert media.captured_at == datetime(2026, 10, 20, 18, 12)


async def test_add_saves_nothing_when_the_upload_fails(s3):
    s3.put.side_effect = _s3_error()
    save_db = MagicMock()

    with _patch_scope(_db_row(_point()), save_db):
        with pytest.raises(StoreUnavailable):
            await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

    save_db.add.assert_not_called()


async def test_add_loses_a_race_for_the_same_point(s3):
    save_db = MagicMock()
    save_db.commit.side_effect = IntegrityError("INSERT", {}, UniqueViolation())

    with _patch_scope(_db_row(_point()), save_db):
        with pytest.raises(PointAlreadyHasMedia):
            await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

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
            await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

    s3.discard.assert_awaited_once_with(s3.put.await_args.args[0])


async def test_add_reports_the_store_unavailable_when_the_point_lookup_fails(s3):
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await MediaStore.add_media("p-1", _OWNER, "photo.jpg", b"data", _CAPTURED_AT)

    s3.put.assert_not_awaited()


# ---- add_media as a contributor ----

async def _add_as_contributor(filename="photo.jpg", captured_at=_CAPTURED_AT):
    return await MediaStore.add_media("p-1", _contributor("c-1"), filename, b"data", captured_at)


async def test_contributor_add_rejects_a_point_that_does_not_exist(s3):
    db = _db_row(None)

    with _patch_scope(db):
        with pytest.raises(NotAuthorized):
            await _add_as_contributor()

    assert db.execute.call_count == 1
    s3.put.assert_not_awaited()


async def test_contributor_add_rejects_a_point_written_by_another_contributor(s3):
    with _patch_scope(_db_row(_point(contributor_id="c-9"))):
        with pytest.raises(NotAuthorized):
            await _add_as_contributor()

    s3.put.assert_not_awaited()


async def test_contributor_add_rejects_a_point_of_the_owner(s3):
    with _patch_scope(_db_row(_point(contributor_id=None))):
        with pytest.raises(NotAuthorized):
            await _add_as_contributor()

    s3.put.assert_not_awaited()


async def test_contributor_add_checks_authorization_before_the_file_type(s3):
    with _patch_scope(_db_row(_point(contributor_id="c-9"))):
        with pytest.raises(NotAuthorized):
            await _add_as_contributor("malware.exe")


async def test_contributor_add_accepts_a_capture_time_in_the_future(s3):
    future = datetime.now(timezone.utc) + timedelta(days=1)

    with _patch_scope(_db_row(_point(contributor_id="c-1")), MagicMock()):
        media = await _add_as_contributor(captured_at=future)

    assert media.point_id == "p-1"


async def test_contributor_add_rejects_an_unsupported_file_type(s3):
    with _patch_scope(_db_row(_point(contributor_id="c-1"))):
        with pytest.raises(UnsupportedMediaType):
            await _add_as_contributor("malware.exe")

    s3.put.assert_not_awaited()


async def test_contributor_add_rejects_a_point_that_already_has_media(s3):
    with _patch_scope(_db_row(_point(contributor_id="c-1", media_id="media-1"))):
        with pytest.raises(PointAlreadyHasMedia):
            await _add_as_contributor()

    s3.put.assert_not_awaited()


async def test_contributor_add_uploads_the_file_and_saves_the_media_for_their_own_point(s3):
    save_db = MagicMock()

    with _patch_scope(_db_row(_point(contributor_id="c-1")), save_db):
        media = await _add_as_contributor("Photo.JPG")

    assert media.point_id == "p-1"
    assert media.content_type == "image/jpeg"
    s3.put.assert_awaited_once_with(media.storage_key, b"data", "image/jpeg")
    save_db.add.assert_called_once_with(media)
    save_db.commit.assert_called_once()


# ---- read_media ----

async def test_read_returns_nothing_for_a_missing_media(s3):
    with _patch_scope(_db_row(None)):
        assert await MediaStore.read_media("media-1", _AS_OWNER) is None

    s3.get.assert_not_awaited()


@pytest.mark.parametrize("user_id", ["someone-else", None])
async def test_read_hides_media_of_a_private_map_from_non_owners(s3, user_id):
    with _patch_scope(_db_row((_media(), _map(), None))):
        assert await MediaStore.read_media("media-1", Credentials(user_id=user_id)) is None

    s3.get.assert_not_awaited()


async def test_read_shows_media_of_a_private_map_to_its_owner(s3):
    media = _media()

    with _patch_scope(_db_row((media, _map(), None))):
        result = await MediaStore.read_media("media-1", _AS_OWNER)

    assert result == (media, "body")
    s3.get.assert_awaited_once_with("media-1.jpg")


async def test_read_shows_media_of_a_public_map_to_anyone(s3):
    media = _media()

    with _patch_scope(_db_row((media, _map(sharing=SharePermission.PUBLIC), None))):
        result = await MediaStore.read_media("media-1", Credentials())

    assert result == (media, "body")


async def test_read_raises_store_unavailable_when_s3_fails(s3):
    s3.get.side_effect = _s3_error()

    with _patch_scope(_db_row((_media(), _map(), None))):
        with pytest.raises(StoreUnavailable):
            await MediaStore.read_media("media-1", _AS_OWNER)


# ---- read_media as a contributor ----

async def _read_as_contributor():
    return await MediaStore.read_media("media-1", _AS_CONTRIBUTOR)


async def test_read_shows_a_contributor_the_media_of_their_own_point_in_a_private_map(s3):
    media = _media()

    with _patch_scope(_db_with_contributor((media, _map(), "c-1"), _contributor("c-1"))):
        result = await _read_as_contributor()

    assert result == (media, "body")


async def test_read_hides_from_a_contributor_the_media_of_another_contributor_in_a_private_map(s3):
    with _patch_scope(_db_with_contributor((_media(), _map(), "c-9"), _contributor("c-1"))):
        assert await _read_as_contributor() is None

    s3.get.assert_not_awaited()


async def test_read_hides_from_a_contributor_the_media_of_the_owner_in_a_private_map(s3):
    with _patch_scope(_db_with_contributor((_media(), _map(), None), _contributor("c-1"))):
        assert await _read_as_contributor() is None


async def test_read_hides_the_media_from_a_removed_contributor(s3):
    removed = _contributor("c-1", removed_at="2026-10-01")

    with _patch_scope(_db_with_contributor((_media(), _map(), "c-1"), removed)):
        assert await _read_as_contributor() is None

    s3.get.assert_not_awaited()


async def test_read_hides_the_media_from_a_secret_that_is_not_a_contributor_of_the_map(s3):
    with _patch_scope(_db_with_contributor((_media(), _map(), "c-1"), None)):
        assert await _read_as_contributor() is None


@pytest.mark.parametrize("map_obj, credentials", [
    (_map(sharing=SharePermission.PUBLIC), _AS_CONTRIBUTOR),
    (_map(), _AS_OWNER),
])
async def test_read_does_not_look_the_contributor_up_when_the_map_is_already_readable(s3, map_obj, credentials):
    db = _db_with_contributor((_media(), map_obj, "c-1"), _contributor("c-1"))

    with _patch_scope(db):
        assert await MediaStore.read_media("media-1", credentials) is not None

    assert db.execute.call_count == 1


async def test_read_does_not_look_for_a_contributor_without_a_secret(s3):
    db = _db_row((_media(), _map(), "c-1"))

    with _patch_scope(db):
        assert await MediaStore.read_media("media-1", Credentials(user_id="someone-else")) is None

    assert db.execute.call_count == 1


async def test_read_reports_the_store_unavailable_when_the_contributor_lookup_fails(s3):
    db = _db_row((_media(), _map(), "c-1"))
    db.execute.return_value.scalar_one_or_none.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _read_as_contributor()


# ---- media_of_map ----

def _found(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _rows(*rows):
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def _db_results(*results):
    db = MagicMock()
    db.execute.side_effect = list(results)
    return db


def _media_of(point_id):
    return Media(id=f"media-{point_id}", point_id=point_id, storage_key=f"media-{point_id}.jpg",
                 content_type="image/jpeg", size=4)


# A point of the owner, one of the contributor c-1 and one of the contributor c-9
_OWNER_MEDIA, _C1_MEDIA, _C9_MEDIA = _media_of("p-owner"), _media_of("p-c1"), _media_of("p-c9")
_MAP_MEDIA = _rows((_OWNER_MEDIA, None), (_C1_MEDIA, "c-1"), (_C9_MEDIA, "c-9"))


async def test_media_of_map_rejects_a_map_that_does_not_exist():
    db = _db_results(_found(None))

    with _patch_scope(db):
        with pytest.raises(MapNotFound):
            await MediaStore.media_of_map("map-1", _AS_OWNER)

    assert db.execute.call_count == 1


async def test_media_of_map_of_a_public_map_is_all_of_it_for_anyone():
    db = _db_results(_found(_map(sharing=SharePermission.PUBLIC)), _MAP_MEDIA)

    with _patch_scope(db):
        media = await MediaStore.media_of_map("map-1", Credentials())

    assert media == [_OWNER_MEDIA, _C1_MEDIA, _C9_MEDIA]
    assert db.execute.call_count == 2


async def test_media_of_map_of_a_private_map_is_all_of_it_for_its_owner():
    with _patch_scope(_db_results(_found(_map()), _MAP_MEDIA)):
        media = await MediaStore.media_of_map("map-1", _AS_OWNER)

    assert media == [_OWNER_MEDIA, _C1_MEDIA, _C9_MEDIA]


@pytest.mark.parametrize("user_id", ["someone-else", None])
async def test_media_of_map_hides_a_private_map_from_a_session_that_does_not_own_it(user_id):
    db = _db_results(_found(_map()), _MAP_MEDIA)

    with _patch_scope(db):
        with pytest.raises(MapNotFound):
            await MediaStore.media_of_map("map-1", Credentials(user_id=user_id))

    assert db.execute.call_count == 1


async def test_media_of_map_shows_a_contributor_only_the_media_of_their_own_points():
    with _patch_scope(_db_results(_found(_map()), _found(_contributor("c-1")), _MAP_MEDIA)):
        media = await MediaStore.media_of_map("map-1", _AS_CONTRIBUTOR)

    assert media == [_C1_MEDIA]


@pytest.mark.parametrize("contributor", [None, _contributor(removed_at="2026-10-01")])
async def test_media_of_map_rejects_a_secret_without_an_active_contributor(contributor):
    with _patch_scope(_db_results(_found(_map()), _found(contributor), _MAP_MEDIA)):
        with pytest.raises(NotAuthorized):
            await MediaStore.media_of_map("map-1", _AS_CONTRIBUTOR)


async def test_media_of_map_of_a_map_without_media_is_empty():
    with _patch_scope(_db_results(_found(_map()), _rows())):
        assert await MediaStore.media_of_map("map-1", _AS_OWNER) == []


async def test_media_of_map_reports_the_store_unavailable_when_the_lookup_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await MediaStore.media_of_map("map-1", _AS_OWNER)
