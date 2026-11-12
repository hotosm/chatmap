"""
The rules of a map over the messages of its groups, and what they do with
a message. A rule has conditions (a text the message says or not, the
group it comes from or not), in groups of all or any of them, and actions:
highlight what matched, suggest a place, suggest a value of a key, or hide
the message (see recognition.rules for how they read it). They only suggest:
a person confirms before a place changes. What they suggest and highlight
is made again for the messages nobody answered when they change; they hide
only messages that arrive after they are saved.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from db import ChatGroup, Map, MapKey, MapKeyValue, MessageRule, Point, session_scope
from recognition.rules import GROUP, SUGGEST_PLACE, SUGGEST_STATUS, every_condition
from results.error import (
    ArchivedValue,
    InvalidRule,
    MapNotFound,
    StoreUnavailable,
    TooManyRules,
    UnknownGroup,
    UnknownKey,
    UnknownPoint,
    UnknownRule,
    UnknownValue,
)

logger = logging.getLogger(__name__)


def _owned_map(db, map_id: str, user_id: str) -> Map:
    """The map, when the user owns it. To anyone else it does not exist: its rules say about its messages."""
    map_obj = db.get(Map, map_id)
    if map_obj is None or map_obj.owner_id != user_id:
        raise MapNotFound
    return map_obj


def _check_refers_to_map(db, map_id: str, rule: dict) -> None:
    """A rule only names groups, places and values of its own map; places (not reports) not removed, values not archived."""
    named = {value for condition in every_condition(rule["conditions"], rule["actions"]) if condition["field"] == GROUP
             for value in condition["values"]}
    if named:
        known = set(db.execute(
            select(ChatGroup.chat).where(ChatGroup.map_id == map_id, ChatGroup.chat.in_(named))
        ).scalars())
        for chat in named - known:
            raise UnknownGroup(chat)
    for action in rule["actions"]:
        if action["type"] == SUGGEST_PLACE:
            point = db.get(Point, action["point_id"])
            if point is None or point.map_id != map_id or point.removed or not point.place:
                raise UnknownPoint(action["point_id"])
        elif action["type"] == SUGGEST_STATUS:
            key = db.get(MapKey, action["key_id"])
            if key is None or key.map_id != map_id or key.archived_at is not None:
                raise UnknownKey(action["key_id"])
            if not key.closed:
                raise InvalidRule("a rule suggests a value of a key with a list")
            value = db.get(MapKeyValue, action["value_id"])
            if value is None or value.key_id != key.id:
                raise UnknownValue(action["value_id"])
            if value.archived_at is not None:
                raise ArchivedValue(action["value_id"])


def _rules_of(db, map_id: str) -> list[MessageRule]:
    return list(db.execute(
        select(MessageRule).where(MessageRule.map_id == map_id).order_by(MessageRule.created_at)
    ).scalars())


def _written(row: MessageRule, rule: dict) -> None:
    row.description = rule["description"]
    row.enabled = rule["enabled"]
    row.conditions = rule["conditions"]
    # Only what each action needs is kept
    row.actions = [{name: value for name, value in action.items() if value is not None} for action in rule["actions"]]


class MessageRulesStore:

    @classmethod
    async def rules(cls, map_id: str, user_id: str) -> list[MessageRule]:
        """The rules of a map, oldest first: they all apply, so their order says nothing."""
        with session_scope() as db:
            try:
                _owned_map(db, map_id, user_id)
                return _rules_of(db, map_id)
            except SQLAlchemyError as error:
                logger.error(f"Fetch rules of map '{map_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def create_rule(cls, map_id: str, user_id: str, rule: dict, max_rules: int) -> MessageRule:
        """A new rule of a map."""
        with session_scope() as db:
            try:
                # Locked, so two rules created at once do not go over the limit
                map_obj = db.execute(select(Map).where(Map.id == map_id).with_for_update()).scalar_one_or_none()
                if map_obj is None or map_obj.owner_id != user_id:
                    raise MapNotFound
                count = db.execute(
                    select(func.count(MessageRule.id)).where(MessageRule.map_id == map_id)
                ).scalar_one()
                if count >= max_rules:
                    raise TooManyRules(max_rules)
                _check_refers_to_map(db, map_id, rule)
                row = MessageRule(map_id=map_id)
                _written(row, rule)
                db.add(row)
                db.commit()
                db.refresh(row)
                return row
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Create rule of map '{map_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def update_rule(cls, map_id: str, rule_id: str, user_id: str, rule: dict) -> MessageRule:
        """A rule as it is written now. Messages it saw before keep what it did to them."""
        with session_scope() as db:
            try:
                _owned_map(db, map_id, user_id)
                row = db.get(MessageRule, rule_id)
                if row is None or row.map_id != map_id:
                    raise UnknownRule(rule_id)
                _check_refers_to_map(db, map_id, rule)
                _written(row, rule)
                row.updated_at = func.now()
                db.commit()
                db.refresh(row)
                return row
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save rule '{rule_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable

    @classmethod
    async def remove_rule(cls, map_id: str, rule_id: str, user_id: str) -> None:
        with session_scope() as db:
            try:
                _owned_map(db, map_id, user_id)
                row = db.get(MessageRule, rule_id)
                if row is None or row.map_id != map_id:
                    raise UnknownRule(rule_id)
                db.delete(row)
                db.commit()
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Remove rule '{rule_id}' failed with: {type(error).__name__}")
                raise StoreUnavailable
