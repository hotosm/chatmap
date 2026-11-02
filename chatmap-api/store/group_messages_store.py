"""
The chat groups a live map listens to and their messages. Only the groups
its owner enabled are kept, and their messages only for as many days as the
map says. The chat of a group and who sent a message are kept as
pseudonyms: they tell two groups or two people apart without saying which.
"""
import asyncio
import hashlib
import hmac
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, exists, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import (
    InterfaceError,
    MultipleResultsFound,
    OperationalError,
    SQLAlchemyError,
)

from data import decrypt_message
from db import ChatGroup, GroupMessage, Map, MapKey, Point, PointTag, PointTagChange, session_scope
from results.error import (
    AlreadyLinked,
    MapNotFound,
    MapNotLive,
    MessageDismissed,
    MessageLinked,
    StoreUnavailable,
    UnknownGroup,
    UnknownKey,
    UnknownMessage,
    UnknownPoint,
)
from settings import CHATMAP_ENC_KEY
from store.point_tags_store import MESSAGE, SET, give_tag, lock_point
from store.received_messages_store import ReceivedMessage

logger = logging.getLogger(__name__)

# How many messages a read returns at most
PAGE_SIZE = 100
# What can be asked of the messages of a map, besides the ones not dismissed
NEW = "new"
LINKED = "linked"
DISMISSED = "dismissed"
# How many days a map can keep the messages of its groups
MAX_KEPT_DAYS = 90
# Longer texts are cut, so a message cannot fill the database
MAX_TEXT_LENGTH = 4000
# How many old messages a prune removes at a time, so it never holds the table long
PRUNE_CHUNK = 1000
# The database did not answer: worth trying again. Any other error is about the data
NOT_ANSWERING = (OperationalError, InterfaceError)


def pseudonym(map_id: str, value: str) -> str:
    # Keyed, so the pseudonym of a phone number cannot be found by trying them all
    digest = hmac.new(CHATMAP_ENC_KEY.encode(), f"{map_id}:{value}".encode(), hashlib.sha256)
    return digest.hexdigest()[:12]


def _sent_at(message: ReceivedMessage) -> datetime:
    sent_at = datetime.fromisoformat(message.date)
    return sent_at if sent_at.tzinfo else sent_at.replace(tzinfo=UTC)


def _live_map_of(db, user_id: str) -> str | None:
    return db.execute(select(Map.id).where(Map.owner_id == user_id, Map.is_live)).scalar_one_or_none()


def _owned_map(db, map_id: str, user_id: str) -> Map:
    """The map, when the user owns it. To anyone else it does not exist: its messages are private."""
    map_obj = db.get(Map, map_id)
    if map_obj is None or map_obj.owner_id != user_id:
        raise MapNotFound
    return map_obj


def _owned_live_map(db, map_id: str, user_id: str) -> Map:
    map_obj = _owned_map(db, map_id, user_id)
    if not map_obj.is_live:
        raise MapNotLive
    return map_obj


def _owned_message(db, message_id: str, user_id: str) -> GroupMessage:
    """
    The message, locked until the transaction ends, when the user owns its
    map and the map listens to its group. To anyone else it does not exist.
    """
    row = db.execute(
        select(GroupMessage, Map.owner_id, ChatGroup.enabled)
        .join(Map, Map.id == GroupMessage.map_id)
        .join(ChatGroup, ChatGroup.id == GroupMessage.group_id)
        .where(GroupMessage.id == message_id)
        .with_for_update(of=GroupMessage)
    ).one_or_none()
    if row is None or row.owner_id != user_id or not row.enabled:
        raise UnknownMessage(message_id)
    return row.GroupMessage


# The changes a message made that are not undone, to points still in its map: what links it to them
def _live_links(message_id, map_id):
    return (
        (PointTagChange.message_id == message_id)
        & (PointTagChange.source == MESSAGE)
        & PointTagChange.undone_at.is_(None)
        & PointTagChange.point_id.in_(select(Point.id).where(Point.map_id == map_id))
    )


def _readable(message: ReceivedMessage) -> tuple[ReceivedMessage, str, str | None, datetime] | None:
    """
    A group message with its text, location and time, or None when it has
    neither text nor location, or cannot be read: one bad message is skipped
    without holding back the others.
    """
    try:
        # Postgres takes no NUL characters in a text
        text = (decrypt_message(message.text) or "").replace("\x00", "")[:MAX_TEXT_LENGTH]
        sent_at = _sent_at(message)
    except (ValueError, TypeError):
        logger.warning(f"Group message '{message.id}' skipped: it could not be read")
        return None
    location = (message.location or "").replace("\x00", "") or None
    return (message, text, location, sent_at) if text or location else None


def _insert(db, rows: list[dict]) -> int:
    kept = db.execute(
        insert(GroupMessage)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["map_id", "stream_id"])
        .returning(GroupMessage.id)
    ).all()
    db.commit()
    return len(kept)


def _insert_one_by_one(db, rows: list[dict]) -> int:
    """After a batch the database did not take: each message on its own, skipping the ones it does not take."""
    kept = 0
    for row in rows:
        try:
            kept += _insert(db, [row])
        except NOT_ANSWERING:
            raise
        except (SQLAlchemyError, ValueError) as error:
            db.rollback()
            logger.warning(f"Group message '{row['stream_id']}' skipped: the database did not take it ({type(error).__name__})")
    return kept


def _keep(device: str, messages: list[tuple[ReceivedMessage, str, str | None, datetime]]) -> int:
    with session_scope() as db:
        try:
            try:
                map_id = _live_map_of(db, device)
            except MultipleResultsFound:
                # Which map they belong to cannot be told, so they are kept in none
                logger.warning(f"Group messages of device '{device}' skipped: its owner has more than one live map")
                return 0
            if map_id is None:
                return 0
            chats = {message.chat: pseudonym(map_id, message.chat) for message, *_ in messages}
            groups = {
                group.chat: group
                for group in db.execute(
                    select(ChatGroup.chat, ChatGroup.id, ChatGroup.enabled_at).where(
                        ChatGroup.map_id == map_id, ChatGroup.enabled, ChatGroup.chat.in_(chats.values()),
                    )
                ).all()
            }
            rows = []
            for message, text, location, sent_at in messages:
                group = groups.get(chats[message.chat])
                # Nothing said in a group before it was enabled is kept. Messages give
                # their time in whole seconds: one sent in the second it was enabled stays
                if group is None or sent_at < group.enabled_at.replace(microsecond=0):
                    continue
                rows.append({
                    "map_id": map_id,
                    "group_id": group.id,
                    "stream_id": message.id,
                    "sender": pseudonym(map_id, message.sender),
                    "text": text,
                    "location": location,
                    "sent_at": sent_at,
                })
            if not rows:
                return 0
            try:
                return _insert(db, rows)
            except NOT_ANSWERING:
                raise
            except (SQLAlchemyError, ValueError):
                # One message the database does not take must not hold back the others
                db.rollback()
                return _insert_one_by_one(db, rows)
        except SQLAlchemyError as error:
            # The error says nothing more: its text would carry the messages
            db.rollback()
            logger.error(f"Save group messages of device '{device}' failed with: {type(error).__name__}")
            raise StoreUnavailable


class GroupMessagesStore:

    @classmethod
    async def save(cls, device: str, messages: list[ReceivedMessage]) -> int:
        """
        Keeps a batch of group messages in the live map of the owner of the
        device that got them, the ones whose group is enabled there. Messages
        without text nor location are skipped; a message read twice is kept
        once. Answers how many were kept now. The database is used from a
        thread, so the API keeps answering meanwhile.
        """
        readable = [found for found in map(_readable, messages) if found]
        if not readable:
            return 0
        return await asyncio.to_thread(_keep, device, readable)

    @classmethod
    async def groups(cls, map_id: str, user_id: str, phone_groups: list[dict]) -> tuple[list[ChatGroup], int]:
        """
        The groups of the phone of the owner of a live map ([{chat, name}],
        as the connector lists them), each with whether the map listens to
        it, and the groups it keeps that the phone no longer has. Also how
        many days the map keeps their messages.
        """
        with session_scope() as db:
            try:
                map_obj = _owned_live_map(db, map_id, user_id)
                kept = {
                    group.chat: group
                    for group in db.execute(select(ChatGroup).where(ChatGroup.map_id == map_id)).scalars()
                }
                groups = []
                for phone_group in phone_groups:
                    chat = pseudonym(map_id, phone_group["chat"])
                    groups.append(kept.pop(chat, None) or ChatGroup(chat=chat, name=phone_group["name"], enabled=False))
                return groups + list(kept.values()), map_obj.messages_kept_days
            except SQLAlchemyError as error:
                logger.error(f"Fetch chat groups of map '{map_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def set_group(
            cls, map_id: str, user_id: str, chat: str, enabled: bool, delete_messages: bool,
            phone_groups: list[dict],
    ) -> ChatGroup:
        """
        Makes a live map listen to a group of the phone (by its pseudonym) or
        stop listening to it. A group stopped keeps its messages until they
        expire, unless delete_messages asks to remove them now.
        """
        with session_scope() as db:
            try:
                _owned_live_map(db, map_id, user_id)
                group = db.execute(
                    select(ChatGroup).where(ChatGroup.map_id == map_id, ChatGroup.chat == chat)
                ).scalar_one_or_none()

                if enabled:
                    # Its name is taken from the phone when the map starts listening to it
                    name = next(
                        (phone_group["name"] for phone_group in phone_groups
                         if pseudonym(map_id, phone_group["chat"]) == chat),
                        None,
                    )
                    if group is None and name is None:
                        raise UnknownGroup(chat)
                    if group is None:
                        # Two enables at once make one group
                        db.execute(
                            insert(ChatGroup)
                            .values(map_id=map_id, chat=chat, name=name)
                            .on_conflict_do_nothing(index_elements=["map_id", "chat"])
                        )
                        group = db.execute(
                            select(ChatGroup).where(ChatGroup.map_id == map_id, ChatGroup.chat == chat)
                        ).scalar_one()
                    if name is not None:
                        group.name = name
                    if not group.enabled:
                        group.enabled = True
                        group.enabled_at = func.now()
                elif group is not None:
                    group.enabled = False
                    if delete_messages:
                        db.execute(delete(GroupMessage).where(GroupMessage.group_id == group.id))
                else:
                    raise UnknownGroup(chat)

                db.commit()
                db.refresh(group)
                return group
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save chat group of map '{map_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def set_kept_days(cls, map_id: str, user_id: str, days: int) -> int:
        """How many days a live map keeps the messages of its groups; older ones go on the next prune."""
        with session_scope() as db:
            try:
                map_obj = _owned_live_map(db, map_id, user_id)
                map_obj.messages_kept_days = days
                db.commit()
                return days
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save days messages are kept in map '{map_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def messages(
            cls, map_id: str, user_id: str, chat: str | None = None, before: tuple[datetime, str] | None = None,
            state: str | None = None,
    ) -> tuple[list[tuple[GroupMessage, str]], dict[str, list[PointTagChange]]]:
        """
        The messages of the groups a map listens to, newest first, each with
        the pseudonym of its group; one group with `chat`. A page holds up to
        PAGE_SIZE messages; `before` (the time and id of the last message of
        a page) asks for the next ones. Both go, since many messages can be
        sent in the same second.

        By default the ones not dismissed; `state` asks for the NEW ones (not
        linked to any point nor dismissed), the LINKED or the DISMISSED. Also
        the changes each message of the page made to points (its links),
        undone ones too, newest first.
        """
        with session_scope() as db:
            try:
                _owned_map(db, map_id, user_id)
                linked = exists().where(_live_links(GroupMessage.id, GroupMessage.map_id))
                query = (
                    select(GroupMessage, ChatGroup.chat)
                    .join(ChatGroup, GroupMessage.group_id == ChatGroup.id)
                    .where(GroupMessage.map_id == map_id, ChatGroup.enabled)
                )
                if state == DISMISSED:
                    query = query.where(GroupMessage.dismissed_at.is_not(None))
                else:
                    query = query.where(GroupMessage.dismissed_at.is_(None))
                if state == NEW:
                    query = query.where(~linked)
                elif state == LINKED:
                    query = query.where(linked)
                if chat is not None:
                    query = query.where(ChatGroup.chat == chat)
                if before is not None:
                    query = query.where(tuple_(GroupMessage.sent_at, GroupMessage.id) < tuple_(*before))
                query = query.order_by(GroupMessage.sent_at.desc(), GroupMessage.id.desc()).limit(PAGE_SIZE)
                rows = [(row.GroupMessage, row.chat) for row in db.execute(query)]
                return rows, _links_of(db, map_id, [message.id for message, _ in rows])
            except SQLAlchemyError as error:
                logger.error(f"Fetch group messages of map '{map_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def link(
            cls, message_id: str, user_id: str, point_id: str, key_id: str, *,
            value_id: str | None = None, value: str | None = None,
    ) -> tuple[PointTagChange, list[PointTag], bool]:
        """
        Gives a point of the map of a message the value of a key the message
        tells (Closed for Status): a change of its tag from the message, at
        the time it was sent. A message can tell about many points. Returns
        the change, what the point has for the key after it, and whether the
        point has it now: a message older than what the point has only goes
        to its history. Undoing the change (PointTagsStore.set_undone) undoes
        the link.
        """
        with session_scope() as db:
            try:
                message = _owned_message(db, message_id, user_id)
                if message.dismissed_at is not None:
                    raise MessageDismissed(message_id)

                row = lock_point(db, point_id)
                if row is None or row.Point.map_id != message.map_id or row.Point.removed:
                    raise UnknownPoint(point_id)
                key = db.get(MapKey, key_id)
                if key is None or key.map_id != message.map_id:
                    raise UnknownKey(key_id)

                # The same message giving the same value to the same point again says nothing new
                same_value = PointTagChange.value_id == value_id if key.closed else PointTagChange.value == value
                twice = db.execute(
                    select(PointTagChange.id).where(
                        _live_links(message.id, message.map_id), PointTagChange.point_id == point_id,
                        PointTagChange.key_id == key_id, PointTagChange.action == SET, same_value,
                    )
                ).scalars().first()
                if twice is not None:
                    raise AlreadyLinked(twice)

                change, current = give_tag(
                    db, point_id, key, SET, value_id, value, message.sent_at, user_id,
                    source=MESSAGE, message_id=message.id,
                )
                db.commit()
                db.refresh(change)
                for tag in current:
                    db.refresh(tag)
                applied = any(
                    tag.confirmed_at == change.happened_at and (tag.value_id, tag.value) == (change.value_id, value)
                    for tag in current
                )
                return change, current, applied
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Link group message '{message_id}' to point '{point_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def set_dismissed(
            cls, message_id: str, user_id: str, dismissed: bool,
    ) -> tuple[GroupMessage, str, list[PointTagChange]]:
        """
        Dismisses a message (it tells nothing about the points of the map) or
        brings it back. A message linked to a point is not dismissed: its
        links are undone first. Returns it with the pseudonym of its group and
        its links, as a read gives them.
        """
        with session_scope() as db:
            try:
                message = _owned_message(db, message_id, user_id)
                if dismissed and message.dismissed_at is None:
                    if db.execute(select(exists().where(_live_links(message.id, message.map_id)))).scalar():
                        raise MessageLinked(message_id)
                    message.dismissed_at = func.now()
                elif not dismissed:
                    message.dismissed_at = None
                db.commit()
                db.refresh(message)
                chat = db.get(ChatGroup, message.group_id).chat
                return message, chat, _links_of(db, message.map_id, [message.id]).get(message.id, [])
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Dismiss group message '{message_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def prune(cls) -> int:
        """Removes the messages each map keeps for longer than it says. Answers how many."""
        return await asyncio.to_thread(_prune)


def _links_of(db, map_id: str, message_ids: list[str]) -> dict[str, list[PointTagChange]]:
    """
    The changes these messages made to points of the map, by message, newest
    first. A point that moved to another map took its links with it.
    """
    if not message_ids:
        return {}
    links = {}
    changes = db.execute(
        select(PointTagChange)
        .join(MapKey, MapKey.id == PointTagChange.key_id)
        .join(Point, Point.id == PointTagChange.point_id)
        # Neither the changes of the keys of a map a point was in before, nor the ones of points that left this map
        .where(
            PointTagChange.message_id.in_(message_ids), PointTagChange.source == MESSAGE,
            MapKey.map_id == map_id, Point.map_id == map_id,
        )
        .order_by(PointTagChange.happened_at.desc(), PointTagChange.id.desc())
    ).scalars()
    for change in changes:
        links.setdefault(change.message_id, []).append(change)
    return links


def _prune() -> int:
    expired = (
        select(GroupMessage.id)
        .join(Map, GroupMessage.map_id == Map.id)
        .where(GroupMessage.sent_at < func.now() - func.make_interval(0, 0, 0, Map.messages_kept_days))
        .limit(PRUNE_CHUNK)
    )
    with session_scope() as db:
        try:
            removed = 0
            while True:
                chunk = db.execute(delete(GroupMessage).where(GroupMessage.id.in_(expired.scalar_subquery()))).rowcount
                db.commit()
                removed += chunk
                if chunk < PRUNE_CHUNK:
                    return removed
        except SQLAlchemyError as error:
            db.rollback()
            logger.error(f"Prune group messages failed with: {type(error).__name__}")
            raise StoreUnavailable
