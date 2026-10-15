from datetime import datetime, timezone

from sqlalchemy import select

from db import Map, Point
from store.media.model import Media


def upload_target(db, point_id: str):
    query = (
        select(Map.owner_id, Media.id, Point.map_id, Point.contributor_id)
        .select_from(Point)
        .join(Map, Map.id == Point.map_id)
        .outerjoin(Media, Media.point_id == Point.id)
        .where(Point.id == point_id)
    )

    return db.execute(query).one_or_none()


def find_for_read(db, media_id: str):
    query = (
        select(Media, Map, Point.contributor_id)
        .join(Point, Point.id == Media.point_id)
        .join(Map, Map.id == Point.map_id)
        .where(Media.id == media_id)
    )

    return db.execute(query).one_or_none()


def insert(db, media_id: str, point_id: str, storage_key: str, content_type: str, size: int,
           captured_at: datetime) -> Media:
    media = Media(
        id=media_id,
        point_id=point_id,
        storage_key=storage_key,
        content_type=content_type,
        size=size,
        captured_at=captured_at.astimezone(timezone.utc).replace(tzinfo=None),
    )
    db.add(media)

    return media
