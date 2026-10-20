"""
The tags of a point as key=value, with memory.

Every change of a tag, or its confirmation, is written down in
point_tag_changes and never removed: undoing one marks it. What a point has
now, point_tags, is always worked out again from those changes after each
write, inside the same transaction and with the point locked, so two writes
at the same time cannot leave them apart.

The time a change happened orders the changes, not the time it was written
down: a change recorded late does not override a newer one.
"""
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from db import Map, MapKey, MapKeyValue, Point, PointTag, PointTagChange, session_scope
from results.error import (
    ArchivedValue,
    InvalidTagValue,
    NotAuthorized,
    StoreUnavailable,
    UnknownKey,
    UnknownTagChange,
    UnknownValue,
)
from store.map_keys_store import readable

logger = logging.getLogger(__name__)

SET = "set"
REMOVE = "remove"
# Sources of a change
MANUAL = "manual"
SYSTEM = "system"


def lock_point(db, point_id: str):
    """
    The point and the owner of its map, locked until the transaction ends,
    or None when there is no such point.
    """
    query = (
        select(Point, Map.owner_id)
        .join(Map, Map.id == Point.map_id)
        .where(Point.id == point_id)
        .with_for_update(of=Point)
    )
    return db.execute(query).one_or_none()


def _identity(change: PointTagChange, key: MapKey):
    # A value of a list is told by its id; a free one, by its text
    return change.value_id if key.closed else change.value


def tags_from_changes(changes: list[PointTagChange], key: MapKey) -> list[PointTag]:
    """
    What a point has for a key, from its changes that were not undone,
    newest first. Each value is the last change that tells about it: set,
    or removed. It has that value since the first of the sets in a row that
    lead to the last one, and it was confirmed by the last one.
    """
    if key.closed:
        # A value that was removed later cannot be given back; removing has no value
        changes = [change for change in changes if change.action != SET or change.value_id is not None]

    # A key with one value is one history; a key with many, one per value
    histories = {}
    for change in changes:
        histories.setdefault(None if key.single else _identity(change, key), []).append(change)

    tags = []
    for history in histories.values():
        last = history[0]
        if last.action != SET:
            continue
        since = last.happened_at
        for change in history[1:]:
            if change.action != SET or _identity(change, key) != _identity(last, key):
                break
            since = change.happened_at
        tags.append(PointTag(
            point_id=last.point_id,
            key_id=key.id,
            single=key.single,
            value_id=last.value_id if key.closed else None,
            value=None if key.closed else last.value,
            since=since,
            confirmed_at=last.happened_at,
            source=last.source,
            user_id=last.user_id,
        ))
    return tags


def refresh_tags(db, point_id: str, key: MapKey) -> None:
    """Work out again what a point has for a key from its changes."""
    changes = list(db.execute(
        select(PointTagChange)
        .where(
            PointTagChange.point_id == point_id,
            PointTagChange.key_id == key.id,
            PointTagChange.undone_at.is_(None),
        )
        .order_by(PointTagChange.happened_at.desc(), PointTagChange.id.desc())
    ).scalars())
    db.execute(delete(PointTag).where(PointTag.point_id == point_id, PointTag.key_id == key.id))
    db.add_all(tags_from_changes(changes, key))
    db.flush()


def record_change(
        db, point_id: str, key: MapKey, action: str, *,
        option: MapKeyValue | None = None, value: str | None = None,
        happened_at: datetime | None = None, source: str = MANUAL,
        user_id: str | None = None, message_id: str | None = None,
) -> PointTagChange:
    """
    Write down a change of a tag of a point and work out again what the
    point has. The point has to be locked (lock_point) by the caller.
    """
    # One clock for both, so a change by hand is not written down before it happened
    now = datetime.now(UTC)
    change = PointTagChange(
        point_id=point_id,
        key_id=key.id,
        action=action,
        value_id=option.id if option is not None else None,
        # The text the value has now, so history keeps it if it is renamed
        value=option.value if option is not None else value,
        happened_at=happened_at or now,
        recorded_at=now,
        source=source,
        user_id=user_id,
        message_id=message_id,
    )
    db.add(change)
    db.flush()
    refresh_tags(db, point_id, key)
    return change


class PointTagsStore:

    @classmethod
    async def history(cls, point_id: str, user_id: str) -> list[tuple[PointTagChange, str]]:
        """
        The changes of the tags of a point, newest first, with the name of
        their key. It tells who did what, so only the owner of the map sees it.
        """
        with session_scope() as db:
            try:
                owner_id = db.execute(
                    select(Map.owner_id).join(Point, Point.map_id == Map.id).where(Point.id == point_id)
                ).scalar_one_or_none()

                if owner_id is None or owner_id != user_id:
                    raise NotAuthorized

                return list(db.execute(
                    select(PointTagChange, MapKey.key)
                    .join(MapKey, MapKey.id == PointTagChange.key_id)
                    .where(PointTagChange.point_id == point_id)
                    .order_by(PointTagChange.happened_at.desc(), PointTagChange.id.desc())
                ).tuples())
            except SQLAlchemyError as error:
                logger.error(f"Fetch tag history of point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def set_undone(cls, change_id: int, user_id: str, undone: bool) -> tuple[PointTagChange, str]:
        """
        Undo a change, or bring back one undone, and work out again what its
        point has. The change stays written down either way. Returns it with
        the name of its key.
        """
        with session_scope() as db:
            try:
                change = db.get(PointTagChange, change_id)
                if change is None:
                    raise UnknownTagChange(change_id)

                row = lock_point(db, change.point_id)
                if row is None or row.owner_id != user_id:
                    raise NotAuthorized

                key = db.get(MapKey, change.key_id)
                if undone and change.undone_at is None:
                    change.undone_at = datetime.now(UTC)
                    change.undone_by = user_id
                elif not undone:
                    change.undone_at = None
                    change.undone_by = None
                db.flush()
                refresh_tags(db, change.point_id, key)
                db.commit()
                db.refresh(change)
                return change, key.key
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Undo tag change '{change_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def read_tags(cls, map_id: str, user_id: str | None) -> list | None:
        """
        What each point of a map has for its keys, or None when the user
        cannot see the map. It does not tell who changed what.
        """
        with session_scope() as db:
            try:
                map_obj, owner = readable(db, map_id, user_id)
                if map_obj is None:
                    return None
                # A point only shows tags of the keys of its own map
                query = (
                    select(
                        PointTag.point_id, PointTag.key_id, PointTag.value_id, PointTag.value,
                        PointTag.since, PointTag.confirmed_at,
                    )
                    .join(Point, Point.id == PointTag.point_id)
                    .join(MapKey, MapKey.id == PointTag.key_id)
                    .where(Point.map_id == map_id, MapKey.map_id == map_id)
                    .order_by(PointTag.point_id, MapKey.position, PointTag.id)
                )
                # Removed points are only shown to the owner of the map
                if not owner:
                    query = query.where(Point.removed.is_(False))
                return db.execute(query).all()
            except SQLAlchemyError as error:
                logger.error(f"Fetch tags of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def set_point_tag(
            cls, point_id: str, key_id: str, user_id: str, action: str, *,
            value_id: str | None = None, value: str | None = None, happened_at: datetime | None = None,
    ) -> list[PointTag]:
        """
        Give a value of a key to a point, confirm it (the same again) or take
        it out, by hand. A key with a list takes the id of one of its options;
        one without, a text. Taking out the value of a key with one value
        needs no value. Returns what the point has for the key after it.
        """
        with session_scope() as db:
            try:
                row = lock_point(db, point_id)
                if row is None or row.owner_id != user_id:
                    raise NotAuthorized

                key = db.get(MapKey, key_id)
                # A point only takes keys of its own map
                if key is None or key.map_id != row.Point.map_id:
                    raise UnknownKey(key_id)

                current = give_tag(db, point_id, key, action, value_id, value, happened_at, user_id)
                db.commit()
                for tag in current:
                    db.refresh(tag)
                return current
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save tag '{key_id}' of point '{point_id}' failed with: '{error}'")
                raise StoreUnavailable


def give_tag(
        db, point_id: str, key: MapKey, action: str, value_id: str | None, value: str | None,
        happened_at: datetime | None, user_id: str,
) -> list[PointTag]:
    """
    Check a change of a tag of a point against its key and write it down;
    the point has to be locked. Taking out what the point does not have
    writes nothing. Returns what the point has for the key after it.
    """
    if action == SET and key.archived_at is not None:
        raise InvalidTagValue("an archived key cannot be given")

    option = None
    needs_value = action == SET or not key.single
    if key.closed:
        if value is not None:
            raise InvalidTagValue("a key with a list takes the id of one of its options")
        if needs_value and value_id is None:
            raise InvalidTagValue("the id of an option is needed")
        if value_id is not None:
            option = db.get(MapKeyValue, value_id)
            if option is None or option.key_id != key.id:
                raise UnknownValue(value_id)
            if action == SET and option.archived_at is not None:
                raise ArchivedValue(value_id)
    else:
        if value_id is not None:
            raise InvalidTagValue("a key without a list takes a text")
        if needs_value and not value:
            raise InvalidTagValue("a text is needed")

    def current() -> list[PointTag]:
        return list(db.execute(
            select(PointTag).where(PointTag.point_id == point_id, PointTag.key_id == key.id).order_by(PointTag.id)
        ).scalars())

    if action == REMOVE:
        has = [tag for tag in current() if key.single or (tag.value_id, tag.value) == (value_id, value)]
        if not has:
            return current()

    record_change(
        db, point_id, key, action, option=option, value=None if key.closed else value,
        happened_at=happened_at, user_id=user_id,
    )
    return current()


def clear_tags_of(db, point_ids: list[str], source: str = SYSTEM) -> None:
    """
    Take out every tag of these points, writing each removal down. Used
    when points move to another map: the keys of the old one are not theirs.
    """
    for tag in db.execute(select(PointTag).where(PointTag.point_id.in_(point_ids))).scalars().all():
        key = db.get(MapKey, tag.key_id)
        option = db.get(MapKeyValue, tag.value_id) if tag.value_id is not None else None
        record_change(
            db, tag.point_id, key, REMOVE, option=option, value=tag.value, source=source,
        )
