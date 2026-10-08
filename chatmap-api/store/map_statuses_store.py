import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from db import Map, MapStatus, Point, SharePermission, session_scope
from results.error import (
    ArchivedStatus,
    NotAuthorized,
    StatusInUse,
    StoreUnavailable,
    UnknownStatus,
)

logger = logging.getLogger(__name__)


class MapStatusesStore:

    @classmethod
    async def statuses_for(cls, map_id: str) -> list[MapStatus]:
        with session_scope() as db:
            try:
                query = select(MapStatus).where(MapStatus.map_id == map_id).order_by(MapStatus.position)
                return list(db.execute(query).scalars())
            except SQLAlchemyError as error:
                logger.error(f"Fetch statuses of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def read_statuses(cls, map_id: str, user_id: str | None) -> tuple[list[MapStatus], list] | None:
        with session_scope() as db:
            try:
                map_obj = db.get(Map, map_id)

                if map_obj is None:
                    return None

                owner = map_obj.owner_id == user_id

                if map_obj.sharing != SharePermission.PUBLIC and not owner:
                    return None

                statuses = list(db.execute(
                    select(MapStatus).where(MapStatus.map_id == map_id).order_by(MapStatus.position)
                ).scalars())

                # A point only shows a status that belongs to its own map
                query = select(Point.id, Point.status_id, Point.status_updated_at).where(
                    Point.map_id == map_id,
                    Point.status_id.in_([status.id for status in statuses]),
                )
                # Removed points are only shown to the owner of the map
                if not owner:
                    query = query.where(Point.removed == False)

                return statuses, db.execute(query).all()
            except SQLAlchemyError as error:
                logger.error(f"Fetch statuses of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def set_statuses(cls, map_id: str, user_id: str, statuses: list[dict]) -> list[MapStatus]:
        with session_scope() as db:
            try:
                map_obj = db.get(Map, map_id)

                if map_obj is None or map_obj.owner_id != user_id:
                    raise NotAuthorized

                # Loaded from the same session that commits, so edits to kept rows persist.
                existing = {
                    row.id: row
                    for row in db.execute(select(MapStatus).where(MapStatus.map_id == map_id)).scalars()
                }
                kept = set()

                for position, status in enumerate(statuses):
                    status_id = status.get("id")
                    # An id that is not of this map is taken as a new status
                    row = existing.get(status_id) if status_id is not None else None

                    if row is None:
                        row = MapStatus(map_id=map_id)
                        db.add(row)
                    else:
                        kept.add(row.id)

                    row.name = status["name"]
                    row.description = status.get("description") or ""
                    row.color = status["color"]
                    # The date of a status already archived is kept
                    if not status.get("archived"):
                        row.archived_at = None
                    elif row.archived_at is None:
                        row.archived_at = datetime.now(UTC)
                    row.position = position

                # A status some points have is not removed, so they do not lose it by mistake
                stale = [row_id for row_id in existing if row_id not in kept]
                if stale:
                    in_use = list(db.execute(
                        select(Point.status_id).where(Point.status_id.in_(stale)).distinct()
                    ).scalars())
                    if in_use:
                        db.rollback()
                        raise StatusInUse(in_use)
                    db.execute(delete(MapStatus).where(MapStatus.id.in_(stale)))

                db.commit()
                logger.debug(f"Statuses saved for map '{map_id}'")
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save statuses of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        return await cls.statuses_for(map_id)

    @classmethod
    async def set_point_status(
            cls, point_id: str, user_id: str, status_id: str | None,
    ) -> tuple[str | None, datetime | None]:
        with session_scope() as db:
            try:
                query = (
                    select(Point, Map.owner_id)
                    .join(Map, Map.id == Point.map_id)
                    .where(Point.id == point_id)
                )
                row = db.execute(query).one_or_none()

                if row is None or row.owner_id != user_id:
                    raise NotAuthorized

                point = row.Point

                if status_id is not None:
                    status = db.get(MapStatus, status_id)
                    # A point only takes a status of its own map
                    if status is None or status.map_id != point.map_id:
                        raise UnknownStatus(status_id)
                    if status.archived_at is not None:
                        raise ArchivedStatus(status_id)

                updated_at = datetime.now(UTC) if status_id else None
                point.status_id = status_id
                point.status_updated_at = updated_at
                db.commit()
                logger.debug(f"Status '{status_id}' saved for point '{point_id}'")
                return status_id, updated_at
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save status of point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable
