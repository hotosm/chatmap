import asyncio
import logging
import uuid
from datetime import datetime
from functools import cache
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.response import StreamingBody
from psycopg2.errors import UniqueViolation
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from db import session_scope, Base, Map, Point, SharePermission
from results.error import (
    StoreUnavailable, NotAuthorized, UnsupportedMediaType, PointAlreadyHasMedia,
)
from settings import S3_ENDPOINT_URL, S3_V2_BUCKET_NAME, S3_ACCESS_KEY, S3_SECRET_KEY

logger = logging.getLogger(__name__)

# Accepted file extensions and the content type each one is served with
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".opus": "audio/opus",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
}


class Media(Base):
    __tablename__ = "media"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    point_id = Column(String, ForeignKey("points.id", ondelete="CASCADE"), nullable=False, unique=True)
    storage_key = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=False), default=datetime.now, nullable=False)


@cache
def _s3_client():
    s3_client_kwargs = {
        'endpoint_url': S3_ENDPOINT_URL,
    }
    if S3_ACCESS_KEY:
        s3_client_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
    if S3_SECRET_KEY:
        s3_client_kwargs['aws_secret_access_key'] = S3_SECRET_KEY
    return boto3.client('s3', **s3_client_kwargs)


async def _put_object(storage_key: str, data: bytes, content_type: str) -> None:
    await asyncio.to_thread(
        lambda: _s3_client().put_object(
            Bucket=S3_V2_BUCKET_NAME, Key=storage_key, Body=data, ContentType=content_type,
        )
    )


async def _get_object(storage_key: str) -> StreamingBody:
    response = await asyncio.to_thread(
        lambda: _s3_client().get_object(Bucket=S3_V2_BUCKET_NAME, Key=storage_key)
    )
    return response["Body"]


async def _discard_object(storage_key: str) -> None:
    try:
        await asyncio.to_thread(
            lambda: _s3_client().delete_object(Bucket=S3_V2_BUCKET_NAME, Key=storage_key)
        )
    except (BotoCoreError, ClientError) as error:
        logger.error(f"Discard orphan media object '{storage_key}' failed with: '{error}'")


class MediaStore:

    # TODO: Break this function down into more descriptive and understandable parts.
    @classmethod
    async def add_media(cls, point_id: str, user_id: str, filename: str, data: bytes) -> Media:
        with session_scope() as db:
            try:
                query = (
                    select(Map.owner_id, Media.id)
                    .select_from(Point)
                    .join(Map, Map.id == Point.map_id)
                    .outerjoin(Media, Media.point_id == Point.id)
                    .where(Point.id == point_id)
                )
                row = db.execute(query).one_or_none()
            except SQLAlchemyError as error:
                logger.error(f"Fetch point '{point_id}' for media failed with: '{error}'")
                raise StoreUnavailable

        if row is None or row.owner_id != user_id:
            raise NotAuthorized

        extension = Path(filename).suffix.lower()
        content_type = CONTENT_TYPES.get(extension)

        if content_type is None:
            raise UnsupportedMediaType(extension)

        if row.id is not None:
            raise PointAlreadyHasMedia(point_id)

        media_id = str(uuid.uuid4())
        storage_key = f"{media_id}{extension}"

        try:
            await _put_object(storage_key, data, content_type)
        except (BotoCoreError, ClientError) as error:
            logger.error(f"Upload media for point '{point_id}' failed with: '{error}'")
            raise StoreUnavailable

        with session_scope() as db:
            try:
                media = Media(
                    id=media_id,
                    point_id=point_id,
                    storage_key=storage_key,
                    content_type=content_type,
                    size=len(data),
                )
                db.add(media)
                db.commit()
                db.refresh(media)
                logger.debug(f"Media '{media_id}' saved for point '{point_id}'")
                return media
            except IntegrityError as error:
                db.rollback()
                await _discard_object(storage_key)

                if isinstance(error.orig, UniqueViolation):
                    raise PointAlreadyHasMedia(point_id)

                logger.error(f"Save media for point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable
            except SQLAlchemyError as error:
                db.rollback()

                await _discard_object(storage_key)

                logger.error(f"Save media for point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def read_media(cls, media_id: str, user_id: str | None) -> tuple[Media, StreamingBody] | None:
        with session_scope() as db:
            try:
                query = (
                    select(Media, Map)
                    .join(Point, Point.id == Media.point_id)
                    .join(Map, Map.id == Point.map_id)
                    .where(Media.id == media_id)
                )
                row = db.execute(query).one_or_none()
            except SQLAlchemyError as error:
                logger.error(f"Fetch media '{media_id}' failed with: '{error}'")
                raise StoreUnavailable

        if row is None:
            return None

        media, map_obj = row

        if map_obj.sharing != SharePermission.PUBLIC and map_obj.owner_id != user_id:
            return None

        try:
            return media, await _get_object(media.storage_key)
        except (BotoCoreError, ClientError) as error:
            logger.error(f"Read media '{media_id}' failed with: '{error}'")
            raise StoreUnavailable
