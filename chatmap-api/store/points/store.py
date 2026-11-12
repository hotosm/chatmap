import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from db import session_scope
from results.error import StoreUnavailable
from store.contributors.authorization import Owner
from store.contributors.model import Contributor
from store.points.cursor import decode_cursor, encode_cursor
from store.points.model import point_id_of
from store.points.repository import history, insert_if_new

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


def _save(db, sender: str, map_id: str, username: str | None, contributor_id: str | None, latitude: float,
          longitude: float, time: datetime, message: str | None) -> PointCreation:
    point_id = point_id_of(sender, map_id, latitude, longitude, time, message)

    try:
        created = insert_if_new(db, point_id, map_id, username, contributor_id, latitude, longitude, time, message)
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


class PointStore:

    @classmethod
    async def create_point(cls, map_id: str, author: Owner | Contributor, latitude: float, longitude: float,
                           time: datetime, message: str | None) -> PointCreation:
        with session_scope() as db:
            if isinstance(author, Owner):
                return _save(db, f"owner:{author.user_id}", map_id, author.username, None, latitude, longitude,
                             time, message)

            return _save(db, f"contributor:{author.id}", map_id, author.nickname, author.id, latitude, longitude,
                         time, message)

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
