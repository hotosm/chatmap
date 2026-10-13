import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from db import session_scope, Map, Point
from results.error import StoreUnavailable, MapNotFound, PointIdAlreadyTaken

logger = logging.getLogger(__name__)


def _owner_of(db, map_id: str) -> str | None:
    return db.execute(select(Map.owner_id).where(Map.id == map_id)).scalar_one_or_none()


def _insert_if_new(db, point_id: str, map_id: str, username: str | None, latitude: float, longitude: float,
                   time: datetime, message: str | None) -> bool:
    query = (
        insert(Point)
        .values(
            id=point_id,
            map_id=map_id,
            geom=f"POINT({longitude} {latitude})",
            time=_as_utc(time),
            message=message,
            username=username,
        )
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(Point.id)
    )
    return db.execute(query).scalar_one_or_none() is not None


def _map_of(db, point_id: str) -> str:
    return db.execute(select(Point.map_id).where(Point.id == point_id)).scalar_one()


def _as_utc(time: datetime) -> datetime:
    return time.astimezone(timezone.utc).replace(tzinfo=None)


class PointStore:

    @classmethod
    async def create_point(cls, point_id: str, map_id: str, user_id: str, username: str | None, latitude: float,
                           longitude: float, time: datetime, message: str | None) -> bool:
        with session_scope() as db:
            try:
                owner_id = _owner_of(db, map_id)
            except SQLAlchemyError as error:
                logger.error(f"Fetch map '{map_id}' for point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable

            if owner_id != user_id:
                raise MapNotFound

            try:
                created = _insert_if_new(db, point_id, map_id, username, latitude, longitude, time, message)
                stored_map_id = map_id if created else _map_of(db, point_id)
                db.commit()
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Create point '{point_id}' on map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        if stored_map_id != map_id:
            raise PointIdAlreadyTaken(point_id)

        return created
