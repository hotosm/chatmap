import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db import Map, MapKey, MapKeyValue, Point, PointTag, session_scope
from results.error import (
    ArchivedStatus,
    ArchivedValue,
    NotAuthorized,
    StatusInUse,
    StoreUnavailable,
    UnknownStatus,
    UnknownValue,
    ValueInUse,
)
from store.map_keys_store import STATUS_KEY, give_tag, readable, save_values, values_of
from store.point_tags_store import REMOVE, SET, lock_point

logger = logging.getLogger(__name__)


def status_key(db, map_id: str, create: bool = False) -> MapKey | None:
    """The status key of a map; created the first time it is needed when asked to."""
    key = db.execute(
        select(MapKey).where(MapKey.map_id == map_id, MapKey.key == STATUS_KEY)
    ).scalar_one_or_none()
    if key is None and create:
        # The status colors the map unless another key already does
        colored = db.execute(
            select(MapKey.id).where(MapKey.map_id == map_id, MapKey.colors_map.is_(True))
        ).first()
        key = MapKey(
            map_id=map_id, key=STATUS_KEY, single=True, closed=True, builtin=True, colors_map=colored is None,
            position=0,
        )
        db.add(key)
        db.flush()
    return key


class MapStatusesStore:

    @classmethod
    async def statuses_for(cls, map_id: str) -> list[MapKeyValue]:
        with session_scope() as db:
            try:
                return values_of(db, status_key(db, map_id))
            except SQLAlchemyError as error:
                logger.error(f"Fetch statuses of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def read_statuses(cls, map_id: str, user_id: str | None) -> tuple[list[MapKeyValue], list] | None:
        with session_scope() as db:
            try:
                map_obj, owner = readable(db, map_id, user_id)
                if map_obj is None:
                    return None

                key = status_key(db, map_id)
                if key is None:
                    return [], []

                # A point only shows a status of its own map: the key is of this map
                query = (
                    select(PointTag.point_id, PointTag.value_id, PointTag.since, PointTag.confirmed_at)
                    .join(Point, Point.id == PointTag.point_id)
                    .where(PointTag.key_id == key.id, Point.map_id == map_id)
                )
                # Removed points are only shown to the owner of the map
                if not owner:
                    query = query.where(Point.removed.is_(False))

                return values_of(db, key), db.execute(query).all()
            except SQLAlchemyError as error:
                logger.error(f"Fetch statuses of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def set_statuses(cls, map_id: str, user_id: str, statuses: list[dict]) -> list[MapKeyValue]:
        with session_scope() as db:
            try:
                map_obj = db.get(Map, map_id)

                if map_obj is None or map_obj.owner_id != user_id:
                    raise NotAuthorized

                # A status some points have is not removed, so they do not lose it by mistake
                try:
                    save_values(db, status_key(db, map_id, create=True), statuses)
                except ValueInUse as in_use:
                    db.rollback()
                    raise StatusInUse(in_use.value_ids)

                db.commit()
                logger.debug(f"Statuses saved for map '{map_id}'")
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save statuses of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        return await cls.statuses_for(map_id)

    @classmethod
    async def set_point_status(
            cls, point_id: str, user_id: str, status_id: str | None, happened_at: datetime | None = None,
    ) -> PointTag | None:
        """
        Give a status to a point, confirm the one it has (the same again) or
        take it out (None), by hand. Returns the status the point has after
        it, which is not the one given when it happened before the last one.
        """
        with session_scope() as db:
            try:
                row = lock_point(db, point_id)

                if row is None or row.owner_id != user_id:
                    raise NotAuthorized

                key = status_key(db, row.Point.map_id, create=status_id is not None)
                if key is None:
                    return None

                try:
                    current = give_tag(
                        db, point_id, key, SET if status_id else REMOVE, status_id, None, happened_at, user_id,
                    )
                except UnknownValue:
                    # A point only takes a status of its own map
                    raise UnknownStatus(status_id)
                except ArchivedValue:
                    raise ArchivedStatus(status_id)

                db.commit()
                for tag in current:
                    db.refresh(tag)
                logger.debug(f"Status '{status_id}' saved for point '{point_id}'")
                return current[0] if current else None
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save status of point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable
