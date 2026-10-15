import logging
import uuid
from datetime import datetime
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from botocore.response import StreamingBody
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from db import session_scope, SharePermission
from results.error import MapNotFound, StoreUnavailable, NotAuthorized, UnsupportedMediaType, PointAlreadyHasMedia
from store.contributors.authorization import Owner, role_in_map
from store.contributors.model import Contributor
from store.credentials import Credentials
from store.media.model import CONTENT_TYPES, Media
from store.media.repository import find_for_read, insert, upload_target
from store.media.storage import discard_object, get_object, put_object

logger = logging.getLogger(__name__)


def _can_read(db, row, credentials: Credentials) -> bool:
    _, map_obj, contributor_id = row

    if map_obj.sharing == SharePermission.PUBLIC:
        return True

    try:
        reader = role_in_map(db, map_obj.id, map_obj.owner_id, credentials)
    except (MapNotFound, NotAuthorized):
        return False

    # The owner reads all the media of the map, a contributor only the media of their own points
    return isinstance(reader, Owner) or reader.id == contributor_id


class MediaStore:

    @classmethod
    async def uploader_of(cls, point_id: str, credentials: Credentials) -> Owner | Contributor:
        with session_scope() as db:
            try:
                row = upload_target(db, point_id)

                if row is None:
                    raise NotAuthorized

                return role_in_map(db, row.map_id, row.owner_id, credentials)
            except MapNotFound:
                # Media answers 403 to a session that does not own the map, not 404 as points do
                raise NotAuthorized
            except SQLAlchemyError as error:
                logger.error(f"Fetch point '{point_id}' and who uploads to it failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def add_media(cls, point_id: str, uploader: Owner | Contributor, filename: str, data: bytes,
                        captured_at: datetime) -> Media:
        with session_scope() as db:
            try:
                row = upload_target(db, point_id)
            except SQLAlchemyError as error:
                logger.error(f"Fetch point '{point_id}' for media failed with: '{error}'")
                raise StoreUnavailable

        # The owner attaches to any point of the map, a contributor only to their own
        if row is None or (not isinstance(uploader, Owner) and row.contributor_id != uploader.id):
            raise NotAuthorized

        return await cls._attach(point_id, row.id, filename, data, captured_at)

    # TODO: Break this function down into more descriptive and understandable parts.
    @classmethod
    async def _attach(cls, point_id: str, existing_media_id: str | None, filename: str, data: bytes,
                      captured_at: datetime) -> Media:
        extension = Path(filename).suffix.lower()
        content_type = CONTENT_TYPES.get(extension)

        if content_type is None:
            raise UnsupportedMediaType(extension)

        if existing_media_id is not None:
            raise PointAlreadyHasMedia(point_id)

        media_id = str(uuid.uuid4())
        storage_key = f"{media_id}{extension}"

        try:
            await put_object(storage_key, data, content_type)
        except (BotoCoreError, ClientError) as error:
            logger.error(f"Upload media for point '{point_id}' failed with: '{error}'")
            raise StoreUnavailable

        with session_scope() as db:
            try:
                media = insert(db, media_id, point_id, storage_key, content_type, len(data), captured_at)
                db.commit()
                db.refresh(media)
                logger.debug(f"Media '{media_id}' saved for point '{point_id}'")
                return media
            except IntegrityError as error:
                db.rollback()
                await discard_object(storage_key)

                if isinstance(error.orig, UniqueViolation):
                    raise PointAlreadyHasMedia(point_id)

                logger.error(f"Save media for point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable
            except SQLAlchemyError as error:
                db.rollback()

                await discard_object(storage_key)

                logger.error(f"Save media for point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def read_media(cls, media_id: str, credentials: Credentials) -> tuple[Media, StreamingBody] | None:
        with session_scope() as db:
            try:
                row = find_for_read(db, media_id)
                allowed = row is not None and _can_read(db, row, credentials)
            except SQLAlchemyError as error:
                logger.error(f"Fetch media '{media_id}' failed with: '{error}'")
                raise StoreUnavailable

        if not allowed:
            return None

        media = row[0]

        try:
            return media, await get_object(media.storage_key)
        except (BotoCoreError, ClientError) as error:
            logger.error(f"Read media '{media_id}' failed with: '{error}'")
            raise StoreUnavailable
