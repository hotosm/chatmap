"""
What the messages of the groups of a map suggest (see store.suggestions), as
the owner of the map sees and answers it: the suggestions of messages, saying
no to one, renewing at once the ones whose places still show what they say,
and reading again, when the words, names or rules of the map change, the
messages nobody answered yet.
"""
import asyncio
import logging

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from db import ChatGroup, GroupMessage, Map, MapKey, MessageSuggestion, Point, PointTagChange, session_scope
from results.error import MessageDismissed, StoreUnavailable, UnknownMessage, UnknownSuggestion
from store.group_messages_store import _live_links, _owned_message
from store.point_tags_store import MESSAGE, RULE, SET, give_tag
from store.suggestions import ACCEPTED, PENDING, REJECTED, ROW_DEFAULTS, suggest, values_now

logger = logging.getLogger(__name__)

# What says a suggestion again, to tell the ones already answered
_SAME = ("line", "point_id", "key_id", "value_id")


class MessageSuggestionsStore:

    @classmethod
    async def suggestions(
            cls, user_id: str, message_ids: list[str],
    ) -> dict[str, list[tuple[MessageSuggestion, bool]]]:
        """
        What messages suggest, by message, the whole message first and then in
        the order of its lines, for the messages of maps the user owns; with
        each one, whether its place has that value now (confirming it renews it).
        """
        if not message_ids:
            return {}
        with session_scope() as db:
            try:
                rows = db.execute(
                    select(MessageSuggestion)
                    .join(GroupMessage, GroupMessage.id == MessageSuggestion.message_id)
                    .join(Map, Map.id == GroupMessage.map_id)
                    .where(MessageSuggestion.message_id.in_(message_ids), Map.owner_id == user_id)
                    .order_by(MessageSuggestion.message_id, MessageSuggestion.line.nulls_first(), MessageSuggestion.id)
                ).scalars().all()
                now = values_now(db, {(row.point_id, row.key_id) for row in rows if row.point_id and row.value_id})
                found: dict[str, list[tuple[MessageSuggestion, bool]]] = {}
                for row in rows:
                    found.setdefault(row.message_id, []).append(
                        (row, row.value_id is not None and row.value_id in now.get((row.point_id, row.key_id), set()))
                    )
                return found
            except SQLAlchemyError as error:
                logger.error(f"Fetch the suggestions of group messages failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def set_rejected(cls, suggestion_id: str, user_id: str, rejected: bool) -> str:
        """
        Says no to a suggestion of a message, or takes that back: it is pending
        again. One already confirmed stays. Returns its message.
        """
        with session_scope() as db:
            try:
                suggestion = db.get(MessageSuggestion, suggestion_id)
                if suggestion is None:
                    raise UnknownSuggestion(suggestion_id)
                # Locks the message, and tells it apart from the ones of maps of others
                _owned_message(db, suggestion.message_id, user_id)
                if suggestion.state != ACCEPTED:
                    suggestion.state = REJECTED if rejected else PENDING
                    suggestion.answered_at = func.now() if rejected else None
                db.commit()
                return suggestion.message_id
            except UnknownMessage:
                raise UnknownSuggestion(suggestion_id)
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Answer suggestion '{suggestion_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def renew(cls, message_id: str, user_id: str, suggestion_ids: list[str]) -> list[PointTagChange]:
        """
        Confirms, in one go, what a message suggests that its places show now:
        the person chose them, and the message says them again at the time it
        was sent, so their values last from then. A suggestion whose place has
        another value by now, or that lacks a place or a value, is left
        pending, to be answered by itself. Returns the changes it made (links
        of the message), newest first.
        """
        with session_scope() as db:
            try:
                message = _owned_message(db, message_id, user_id)
                if message.dismissed_at is not None:
                    raise MessageDismissed(message_id)
                chosen = db.execute(
                    select(MessageSuggestion).where(
                        MessageSuggestion.message_id == message_id, MessageSuggestion.id.in_(suggestion_ids),
                        MessageSuggestion.state == PENDING,
                        MessageSuggestion.point_id.is_not(None), MessageSuggestion.value_id.is_not(None),
                    ).order_by(MessageSuggestion.line.nulls_first(), MessageSuggestion.id)
                ).scalars().all()
                # Only places and keys of the map of the message, as a link: the places
                # locked in one go, in the order of their ids as any lock of many
                places = set(db.execute(
                    select(Point.id).where(
                        Point.id.in_({suggestion.point_id for suggestion in chosen}),
                        Point.map_id == message.map_id, Point.removed.is_not(True),
                    ).order_by(Point.id).with_for_update()
                ).scalars())
                keys = {key.id: key for key in db.execute(
                    select(MapKey).where(
                        MapKey.id.in_({suggestion.key_id for suggestion in chosen}), MapKey.map_id == message.map_id,
                    )
                ).scalars()}
                # Read after the lock: someone may have changed them since the screen showed them
                now = values_now(db, {
                    (suggestion.point_id, suggestion.key_id) for suggestion in chosen
                    if suggestion.point_id in places and suggestion.key_id in keys
                })
                renewed = []
                for suggestion in chosen:
                    if suggestion.value_id not in now.get((suggestion.point_id, suggestion.key_id), set()):
                        continue
                    change, _ = give_tag(
                        db, suggestion.point_id, keys[suggestion.key_id], SET, suggestion.value_id, None,
                        message.sent_at, user_id,
                        source=RULE if suggestion.rule_id else MESSAGE, message_id=message.id,
                    )
                    suggestion.state = ACCEPTED
                    suggestion.answered_at = func.now()
                    renewed.append(change)
                db.commit()
                for change in renewed:
                    db.refresh(change)
                return renewed[::-1]
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Renew suggestions of group message '{message_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def reread(cls, map_id: str) -> int:
        """
        Reads again, with the words, names and rules the map has now, the
        messages it keeps that nobody answered yet: without links to places,
        and in sight or hidden by a rule. Their pending suggestions are made
        again; what a person already answered is not suggested again. A rule
        hides what arrives: what is in sight stays so, and what a rule hid
        comes back when no rule hides it any more. Called after the owner
        changes any of them, already saved: when reading fails, the
        suggestions stay as they were. Returns how many messages suggest
        something now.
        """
        return await asyncio.to_thread(_reread, map_id)


def _waiting(map_id: str):
    """The messages of a map nobody answered: not dismissed by a person, and without links to places."""
    return and_(
        GroupMessage.map_id == map_id, ChatGroup.enabled,
        or_(GroupMessage.dismissed_at.is_(None), GroupMessage.dismissed_by_rule),
        ~exists().where(_live_links(GroupMessage.id, GroupMessage.map_id)),
    )


def _reread(map_id: str) -> int:
    with session_scope() as db:
        try:
            # Locked first, so a person answering one of them now goes before or after this, never in between
            ids = db.execute(
                select(GroupMessage.id).join(ChatGroup, ChatGroup.id == GroupMessage.group_id)
                .where(_waiting(map_id)).order_by(GroupMessage.id).with_for_update(of=GroupMessage)
            ).scalars().all()
            if not ids:
                return 0
            # Read again once locked: what a person did while this waited is seen now
            messages = db.execute(
                select(
                    GroupMessage.id, GroupMessage.group_id, GroupMessage.text, GroupMessage.sent_at,
                    GroupMessage.dismissed_at, ChatGroup.chat,
                )
                .join(ChatGroup, ChatGroup.id == GroupMessage.group_id)
                .where(GroupMessage.id.in_(ids), _waiting(map_id))
            ).all()
            if not messages:
                return 0
            ids = [message.id for message in messages]
            answered = {
                (row.message_id, *(getattr(row, column) for column in _SAME))
                for row in db.execute(
                    select(MessageSuggestion).where(
                        MessageSuggestion.message_id.in_(ids), MessageSuggestion.state != PENDING,
                    )
                ).scalars()
            }
            db.execute(delete(MessageSuggestion).where(
                MessageSuggestion.message_id.in_(ids), MessageSuggestion.state == PENDING,
            ))
            rows = [
                {
                    "id": message.id, "group_id": message.group_id, "text": message.text, "sent_at": message.sent_at,
                    **ROW_DEFAULTS,
                }
                for message in messages
            ]
            made = suggest(db, map_id, rows, {message.id: message.chat for message in messages})
            for row, message in zip(rows, messages):
                if message.dismissed_at is None:
                    # In sight: a rule that hides now does it with what arrives from now on
                    row["dismissed_at"], row["dismissed_by_rule"] = None, False
                elif row["dismissed_by_rule"]:
                    # Still hidden by a rule, since it was
                    row["dismissed_at"] = message.dismissed_at
            # What the rules do to them now, in one update by id
            db.execute(update(GroupMessage), [
                {key: row[key] for key in ("id", "highlights", "dismissed_at", "dismissed_by_rule")} for row in rows
            ])
            new = [
                item for items in made.values() for item in items
                if (item["message_id"], *(item[column] for column in _SAME)) not in answered
            ]
            if new:
                db.execute(insert(MessageSuggestion).values(new))
            db.commit()
            return len({item["message_id"] for item in new})
        except SQLAlchemyError as error:
            db.rollback()
            # What the owner changed is saved: the suggestions wait for the next change
            logger.error(f"Read again the messages of map '{map_id}' failed with: {type(error).__name__}")
            return 0
