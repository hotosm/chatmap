"""
The other names of the places of a map, as the chats write them ("Ein
Rihan", "عين الريحان"): a line of a message that says one of them names the
place (see recognition.vocabulary). Only the owner of the map sees and writes them.
"""
import logging

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from db import Map, PlaceName, Point, session_scope
from results.error import StoreUnavailable, UnknownPoint

logger = logging.getLogger(__name__)


def _owned_point(db, point_id: str, user_id: str) -> Point:
    """The place, when the user owns its map and it was not removed. A report has no other names; to anyone else it does not exist."""
    row = db.execute(
        select(Point, Map.owner_id).join(Map, Map.id == Point.map_id).where(Point.id == point_id)
    ).one_or_none()
    if row is None or row.owner_id != user_id or row.Point.removed or not row.Point.place:
        raise UnknownPoint(point_id)
    return row.Point


def names_of(db, point_ids) -> dict[str, list[str]]:
    """The other names of points, by point, in their order."""
    names: dict[str, list[str]] = {}
    for point_id, name in db.execute(
        select(PlaceName.point_id, PlaceName.name)
        .where(PlaceName.point_id.in_(point_ids))
        .order_by(PlaceName.point_id, PlaceName.position)
    ).all():
        names.setdefault(point_id, []).append(name)
    return names


class PlaceNamesStore:

    @classmethod
    async def names(cls, point_id: str, user_id: str) -> list[str]:
        with session_scope() as db:
            try:
                _owned_point(db, point_id, user_id)
                return names_of(db, [point_id]).get(point_id, [])
            except SQLAlchemyError as error:
                logger.error(f"Fetch the names of point '{point_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def set_names(cls, point_id: str, user_id: str, names: list[str]) -> tuple[str, list[str]]:
        """The other names of a point, instead of the ones it had, in this order. Returns its map and them."""
        with session_scope() as db:
            try:
                point = _owned_point(db, point_id, user_id)
                db.execute(delete(PlaceName).where(PlaceName.point_id == point_id))
                db.add_all(PlaceName(point_id=point_id, name=name, position=i) for i, name in enumerate(names))
                db.commit()
                return point.map_id, names
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save the names of point '{point_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable
