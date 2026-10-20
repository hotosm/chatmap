"""
The keys a map defines for the tags of its points (status, a category, the
fuel there is...) and the options of the ones with a list.

The status is a key of the system: it cannot be removed nor renamed, and
the routes of statuses keep working on it. Free tags are not keys: they
stay as text in points.tags.
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from db import Map, MapKey, MapKeyValue, Point, PointTag, PointTagChange, SharePermission, session_scope
from results.error import (
    ArchivedValue,
    BuiltinKey,
    InvalidTagValue,
    KeyInUse,
    KeyNameTaken,
    NotAuthorized,
    StoreUnavailable,
    UnknownKey,
    UnknownValue,
    ValueInUse,
)
from store.point_tags_store import REMOVE, SET, lock_point, record_change

logger = logging.getLogger(__name__)

# The key of the system, by the name it has in every map
STATUS_KEY = "status"


def values_of(db, key: MapKey | None) -> list[MapKeyValue]:
    if key is None:
        return []
    return list(db.execute(
        select(MapKeyValue).where(MapKeyValue.key_id == key.id).order_by(MapKeyValue.position)
    ).scalars())


def save_values(db, key: MapKey, values: list[dict]) -> None:
    """
    Save the whole list of options of a key, in the given order. An option
    with the id of one of the key is edited, any other is new; one left out
    is removed, which is only possible when no point has it.
    """
    existing = {row.id: row for row in values_of(db, key)}
    kept = set()

    for position, value in enumerate(values):
        value_id = value.get("id")
        # An id that is not of this key is taken as a new option
        row = existing.get(value_id) if value_id is not None else None

        if row is None:
            row = MapKeyValue(key_id=key.id)
            db.add(row)
        else:
            kept.add(row.id)

        row.value = value["name"]
        row.description = value.get("description") or ""
        row.color = value.get("color")
        hours = value.get("expires_after")
        row.expires_after = timedelta(hours=hours) if hours else None
        # The date of an option already archived is kept
        if not value.get("archived"):
            row.archived_at = None
        elif row.archived_at is None:
            row.archived_at = datetime.now(UTC)
        row.position = position

    # An option some points have is not removed, so they do not lose it by mistake
    stale = [row_id for row_id in existing if row_id not in kept]
    if stale:
        in_use = list(db.execute(
            select(PointTag.value_id).where(PointTag.value_id.in_(stale)).distinct()
        ).scalars())
        if in_use:
            raise ValueInUse(in_use)
        db.execute(delete(MapKeyValue).where(MapKeyValue.id.in_(stale)))
    db.flush()


def readable(db, map_id: str, user_id: str | None) -> tuple[Map | None, bool]:
    """The map when the user can see it (its owner, or anyone if public), and if it is the owner."""
    map_obj = db.get(Map, map_id)
    if map_obj is None:
        return None, False
    owner = map_obj.owner_id == user_id
    if map_obj.sharing != SharePermission.PUBLIC and not owner:
        return None, False
    return map_obj, owner


def _owned(db, map_id: str, user_id: str) -> Map:
    map_obj = db.get(Map, map_id)
    if map_obj is None or map_obj.owner_id != user_id:
        raise NotAuthorized
    return map_obj


def _color_map_by(db, map_id: str, key: MapKey | None) -> None:
    """Make a key the one that colors the map by default, or none."""
    db.execute(update(MapKey).where(MapKey.map_id == map_id, MapKey.colors_map.is_(True)).values(colors_map=False))
    db.flush()
    if key is not None:
        key.colors_map = True
        db.flush()


def _name_taken(db, map_id: str, name: str, but: str | None = None) -> bool:
    query = select(MapKey.id).where(MapKey.map_id == map_id, func.lower(MapKey.key) == name.lower())
    if but is not None:
        query = query.where(MapKey.id != but)
    return name.lower() == STATUS_KEY or db.execute(query).first() is not None


class MapKeysStore:

    @classmethod
    async def read_keys(cls, map_id: str, user_id: str | None) -> list[tuple[MapKey, list[MapKeyValue]]] | None:
        """The keys of a map with their options, in order, or None when the user cannot see it."""
        with session_scope() as db:
            try:
                map_obj, _ = readable(db, map_id, user_id)
                if map_obj is None:
                    return None
                keys = db.execute(
                    select(MapKey).where(MapKey.map_id == map_id).order_by(MapKey.position, MapKey.key)
                ).scalars()
                return [(key, values_of(db, key)) for key in keys]
            except SQLAlchemyError as error:
                logger.error(f"Fetch keys of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def create_key(
            cls, map_id: str, user_id: str, key: dict, max_keys: int,
    ) -> tuple[MapKey, list[MapKeyValue]]:
        with session_scope() as db:
            try:
                _owned(db, map_id, user_id)
                if _name_taken(db, map_id, key["key"]):
                    raise KeyNameTaken(key["key"])
                # The keys of the system and the archived ones do not count
                count = db.execute(select(func.count(MapKey.id)).where(
                    MapKey.map_id == map_id, MapKey.builtin.is_(False), MapKey.archived_at.is_(None),
                )).scalar()
                if count >= max_keys:
                    raise InvalidTagValue(f"a map takes up to {max_keys} keys of its own")
                if not key["closed"] and key.get("values"):
                    raise InvalidTagValue("a key without a list has no options")

                last = db.execute(select(func.max(MapKey.position)).where(MapKey.map_id == map_id)).scalar()
                row = MapKey(
                    map_id=map_id, key=key["key"], single=key["single"], closed=key["closed"], builtin=False,
                    position=(last or 0) + 1,
                )
                db.add(row)
                db.flush()
                save_values(db, row, key.get("values") or [])
                if key.get("colors_map"):
                    _color_map_by(db, map_id, row)
                db.commit()
                return row, values_of(db, row)
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Create key in map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def update_key(
            cls, map_id: str, key_id: str, user_id: str, changes: dict,
    ) -> tuple[MapKey, list[MapKeyValue]]:
        """
        Rename a key, archive it or bring it back, or save its options. Whether
        it takes one value or many, and from a list or not, does not change.
        """
        with session_scope() as db:
            try:
                _owned(db, map_id, user_id)
                row = db.get(MapKey, key_id)
                if row is None or row.map_id != map_id:
                    raise UnknownKey(key_id)

                name = changes.get("key")
                if name is not None and name != row.key:
                    if row.builtin:
                        raise BuiltinKey(key_id)
                    if _name_taken(db, map_id, name, but=row.id):
                        raise KeyNameTaken(name)
                    row.key = name

                archived = changes.get("archived")
                if archived is not None:
                    if row.builtin and archived:
                        raise BuiltinKey(key_id)
                    if not archived:
                        row.archived_at = None
                    elif row.archived_at is None:
                        row.archived_at = datetime.now(UTC)

                colors_map = changes.get("colors_map")
                if colors_map is not None and colors_map != row.colors_map:
                    _color_map_by(db, map_id, row if colors_map else None)

                values = changes.get("values")
                if values is not None:
                    if not row.closed and values:
                        raise InvalidTagValue("a key without a list has no options")
                    save_values(db, row, values)

                db.commit()
                return row, values_of(db, row)
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Update key '{key_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def remove_key(cls, map_id: str, key_id: str, user_id: str) -> None:
        """
        Remove a key that was never given to a point; removing it would take
        its history away. One that was used can only be archived.
        """
        with session_scope() as db:
            try:
                _owned(db, map_id, user_id)
                row = db.get(MapKey, key_id)
                if row is None or row.map_id != map_id:
                    raise UnknownKey(key_id)
                if row.builtin:
                    raise BuiltinKey(key_id)
                used = db.execute(select(PointTagChange.id).where(PointTagChange.key_id == key_id).limit(1)).first()
                if used is not None:
                    raise KeyInUse(key_id)
                db.delete(row)
                db.commit()
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Remove key '{key_id}' failed with: '{error}'")
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
        db, point_id, key, action, value_row=option, value=None if key.closed else value,
        happened_at=happened_at, user_id=user_id,
    )
    return current()


def clear_tags_of(db, point_ids: list[str], source: str = "system") -> None:
    """
    Take out every tag of these points, writing each removal down. Used
    when points move to another map: the keys of the old one are not theirs.
    """
    for tag in db.execute(select(PointTag).where(PointTag.point_id.in_(point_ids))).scalars().all():
        key = db.get(MapKey, tag.key_id)
        option = db.get(MapKeyValue, tag.value_id) if tag.value_id is not None else None
        record_change(
            db, tag.point_id, key, REMOVE, value_row=option, value=tag.value, source=source,
        )
