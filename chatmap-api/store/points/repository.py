from datetime import datetime

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert

from db import Point
from store.media.model import Media
from store.points.model import as_utc


def insert_if_new(db, point_id: str, map_id: str, username: str | None, contributor_id: str | None,
                  latitude: float, longitude: float, time: datetime, message: str | None) -> bool:
    query = (
        insert(Point)
        .values(
            id=point_id,
            map_id=map_id,
            geom=f"POINT({longitude} {latitude})",
            time=as_utc(time),
            message=message,
            username=username,
            contributor_id=contributor_id,
        )
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(Point.id)
    )
    return db.execute(query).scalar_one_or_none() is not None


def history(db, map_id: str, contributor_id: str, after: tuple[datetime, str] | None, limit: int):
    query = (
        select(
            Point.id,
            Point.time,
            func.ST_Y(Point.geom),
            func.ST_X(Point.geom),
            Point.message,
            Media.id,
            Media.content_type,
            Media.size,
            Media.captured_at,
        )
        .select_from(Point)
        .outerjoin(Media, Media.point_id == Point.id)
        .where(Point.map_id == map_id, Point.contributor_id == contributor_id, Point.removed.is_(False))
        .order_by(Point.time.desc(), Point.id.desc())
        .limit(limit)
    )

    if after is not None:
        query = query.where(tuple_(Point.time, Point.id) < tuple_(*after))

    return db.execute(query).all()
