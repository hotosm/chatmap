import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from db import Map, Point, session_scope
from results.error import PlaceNameTaken, StoreUnavailable, UnknownPoint
from store.contributors.authorization import Owner
from store.contributors.model import Contributor
from store.points.cursor import decode_cursor, encode_cursor
from store.points.model import point_id_of, same_name
from store.points.repository import history, insert_if_new, place_names

logger = logging.getLogger(__name__)

HISTORY_PAGE_SIZE = 50


@dataclass(frozen=True)
class PointCreation:
    id: str
    created: bool


@dataclass(frozen=True)
class HistoryMedia:
    id: str
    content_type: str
    size: int
    captured_at: datetime | None


@dataclass(frozen=True)
class HistoryPoint:
    id: str
    time: datetime
    latitude: float
    longitude: float
    message: str | None
    media: HistoryMedia | None


@dataclass(frozen=True)
class HistoryPage:
    points: list[HistoryPoint]
    next: str | None


def _save(db, point_id: str, map_id: str, username: str | None, contributor_id: str | None, latitude: float,
          longitude: float, time: datetime, message: str | None, place: bool = False,
          name: str | None = None) -> PointCreation:
    try:
        created = insert_if_new(db, point_id, map_id, username, contributor_id, latitude, longitude, time, message,
                                place, name)
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        logger.error(f"Create point '{point_id}' on map '{map_id}' failed with: '{error}'")
        raise StoreUnavailable

    return PointCreation(id=point_id, created=created)


def _history_point(row) -> HistoryPoint:
    media = HistoryMedia(
        id=row[5],
        content_type=row[6],
        size=row[7],
        captured_at=row[8].replace(tzinfo=timezone.utc) if row[8] is not None else None,
    ) if row[5] is not None else None

    return HistoryPoint(
        id=row[0],
        time=row[1].replace(tzinfo=timezone.utc),
        latitude=row[2],
        longitude=row[3],
        message=row[4],
        media=media,
    )


def _check_name_free(db, map_id: str, name: str | None, point_id: str) -> None:
    """
    A place has a name no other place of its map has (see same_name). The
    same place asked for again is not another one: it is answered as it is.
    """
    if not same_name(name):
        return
    try:
        taken = any(
            same_name(other) == same_name(name) and other_id != point_id for other_id, other in place_names(db, map_id)
        )
    except SQLAlchemyError as error:
        logger.error(f"Read the places of map '{map_id}' failed with: '{error}'")
        raise StoreUnavailable
    if taken:
        raise PlaceNameTaken(name)


class PointStore:

    @classmethod
    async def create_point(cls, map_id: str, author: Owner | Contributor, latitude: float, longitude: float,
                           time: datetime, message: str | None) -> PointCreation:
        with session_scope() as db:
            # What the owner makes is a place of the map; what a contributor sends, a report
            # (what the owner writes is the name of the place, not something said)
            if isinstance(author, Owner):
                point_id = point_id_of(f"owner:{author.user_id}", map_id, latitude, longitude, time, message)
                _check_name_free(db, map_id, message, point_id)
                name = message.strip() if message and message.strip() else None
                return _save(db, point_id, map_id, author.username, None, latitude, longitude, time, None,
                             place=True, name=name)

            point_id = point_id_of(f"contributor:{author.id}", map_id, latitude, longitude, time, message)
            return _save(db, point_id, map_id, author.nickname, author.id, latitude, longitude, time, message)

    @classmethod
    async def name_point(cls, point_id: str, user_id: str, name: str) -> tuple[str, bool]:
        """
        Gives a name to a point of a map the user owns. A place takes it
        instead of the one it had; a report (sent from the field or a chat)
        becomes a place with it, keeping what it said. Returns the map of the
        point and whether it was a report.
        """
        with session_scope() as db:
            try:
                point = db.get(Point, point_id)
                if point is None or point.removed:
                    raise UnknownPoint(point_id)
                # Locked, so two names given at once in a map are not the same one
                owner_id = db.execute(
                    select(Map.owner_id).where(Map.id == point.map_id).with_for_update()
                ).scalar_one()
                # To anyone else, the point of a map they do not own does not exist
                if owner_id != user_id:
                    raise UnknownPoint(point_id)
                _check_name_free(db, point.map_id, name, point_id)
                was_report = not point.place
                point.name = name
                point.place = True
                db.commit()
                return point.map_id, was_report
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Name point '{point_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def contributor_points(cls, map_id: str, contributor: Contributor, cursor: str | None) -> HistoryPage:
        after = decode_cursor(cursor) if cursor is not None else None

        with session_scope() as db:
            try:
                rows = history(db, map_id, contributor.id, after, HISTORY_PAGE_SIZE + 1)
            except SQLAlchemyError as error:
                logger.error(f"List points of contributor '{contributor.id}' on map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        page = rows[:HISTORY_PAGE_SIZE]
        next_cursor = encode_cursor(page[-1][1], page[-1][0]) if len(rows) > HISTORY_PAGE_SIZE else None

        return HistoryPage(points=[_history_point(row) for row in page], next=next_cursor)
