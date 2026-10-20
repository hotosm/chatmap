"""
The keys a map defines for the tags of its points (a status, the fuel
there is, a category...) and the values of the ones with a list, which the
screen calls options. All keys are alike; one of them may color the map.
Free tags are not keys: they stay as text in points.tags.
"""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from db import Map, MapKey, MapKeyValue, PointTag, PointTagChange, SharePermission, session_scope
from results.error import (
    InvalidTagValue,
    KeyInUse,
    KeyNameTaken,
    NotAuthorized,
    StoreUnavailable,
    TooManyKeys,
    UnknownKey,
    ValueInUse,
)

logger = logging.getLogger(__name__)


def values_of(db, key: MapKey) -> list[MapKeyValue]:
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

        row.value = value["value"]
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
        if db.execute(select(PointTag.id).where(PointTag.value_id.in_(stale)).limit(1)).first():
            raise ValueInUse(stale)
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


def _owned(db, map_id: str, user_id: str) -> None:
    map_obj = db.get(Map, map_id)
    if map_obj is None or map_obj.owner_id != user_id:
        raise NotAuthorized


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
    return db.execute(query).first() is not None


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
                # The archived ones do not count
                count = db.execute(select(func.count(MapKey.id)).where(
                    MapKey.map_id == map_id, MapKey.archived_at.is_(None),
                )).scalar()
                if count >= max_keys:
                    raise TooManyKeys(max_keys)
                if not key["closed"] and key.get("values"):
                    raise InvalidTagValue("a key without a list has no options")

                last = db.execute(select(func.max(MapKey.position)).where(MapKey.map_id == map_id)).scalar()
                row = MapKey(
                    map_id=map_id, key=key["key"], single=key["single"], closed=key["closed"],
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
                    if _name_taken(db, map_id, name, but=row.id):
                        raise KeyNameTaken(name)
                    row.key = name

                archived = changes.get("archived")
                if archived is not None:
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
                used = db.execute(select(PointTagChange.id).where(PointTagChange.key_id == key_id).limit(1)).first()
                if used is not None:
                    raise KeyInUse(key_id)
                db.delete(row)
                db.commit()
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Remove key '{key_id}' failed with: '{error}'")
                raise StoreUnavailable
