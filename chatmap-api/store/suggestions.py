"""
What the rules and the words of a map suggest for the messages of its groups:
rows of message_suggestions, each a place, a value of a key, or both, pending
for a person. Nothing here changes a place.

- The words of the values and the names of the places read each line of a
  message (recognition.vocabulary): a suggestion per place and value a line says.
- Every rule a message meets applies, in no order (recognition.rules): its
  place and value, for the whole message. What a line already suggests for a
  place says it better, so a rule does not repeat it.
- A suggestion is doubtful when its line (or, for a rule, the message) asks,
  or when two of them give one key of a place different values.

A message a rule hides suggests nothing. A link of a message to a place
answers the suggestions about that place and key (answer_on_link).
"""
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select, tuple_

from db import ChatGroupPoint, MapKey, MapKeyValue, MessageRule, MessageSuggestion, Point, PointTag
from recognition import vocabulary
from recognition.languages import asks, languages
from recognition.rules import Outcome, outcomes
from store.place_names_store import names_of

logger = logging.getLogger(__name__)

# The states of a suggestion
PENDING = "pending"
ACCEPTED = "accepted"
REJECTED = "rejected"

# What a message has before rules read it; every row of a batch has the same columns
ROW_DEFAULTS = {"highlights": None, "dismissed_at": None, "dismissed_by_rule": False}


def rules_of(db, map_id: str) -> list[MessageRule]:
    """The enabled rules of a map: they all apply, so their order says nothing."""
    return list(db.execute(
        select(MessageRule).where(MessageRule.map_id == map_id, MessageRule.enabled).order_by(MessageRule.created_at)
    ).scalars())


def _still_there(db, map_id: str, rules: list[MessageRule]) -> tuple[set, set]:
    """
    The places and values the rules suggest that a map still has: places not
    removed, and values not archived of keys with a list not archived. A
    rule saved earlier can name one that went since.
    """
    actions = [action for rule in rules for action in rule.actions]
    point_ids = {action["point_id"] for action in actions if action.get("point_id")}
    value_ids = {action["value_id"] for action in actions if action.get("value_id")}
    points = set(db.execute(
        select(Point.id).where(Point.id.in_(point_ids), Point.map_id == map_id, Point.place, Point.removed.is_(False))
    ).scalars()) if point_ids else set()
    values = set(db.execute(
        select(MapKeyValue.id)
        .join(MapKey, MapKey.id == MapKeyValue.key_id)
        .where(
            MapKeyValue.id.in_(value_ids), MapKey.map_id == map_id, MapKey.closed,
            MapKey.archived_at.is_(None), MapKeyValue.archived_at.is_(None),
        )
    ).scalars()) if value_ids else set()
    return points, values


def _reader_of(db, map_id: str) -> vocabulary.Reader | None:
    """
    The words of a map ready to read its messages; None when no value has
    words. The values are the ones not archived of keys with a list not
    archived, and the places, the places not removed with a name, by it and
    by their other names.
    """
    values = db.execute(
        select(MapKeyValue.id, MapKeyValue.key_id, MapKeyValue.words)
        .join(MapKey, MapKey.id == MapKeyValue.key_id)
        .where(
            MapKey.map_id == map_id, MapKey.closed, MapKey.archived_at.is_(None),
            MapKeyValue.archived_at.is_(None), func.jsonb_array_length(MapKeyValue.words) > 0,
        )
    ).all()
    if not values:
        return None
    points = db.execute(
        select(Point.id, Point.message).where(
            Point.map_id == map_id, Point.place, Point.removed.is_(False), Point.message.is_not(None), Point.message != "",
        )
    ).all()
    other_names = names_of(db, [point.id for point in points])
    return vocabulary.compile_map(
        [vocabulary.Place(point.id, (point.message, *other_names.get(point.id, []))) for point in points],
        [vocabulary.Value(value.id, value.key_id, tuple(value.words)) for value in values],
    )


def _group_places(db, group_ids: set[str]) -> dict[str, tuple[str, ...]]:
    """The places each chat group is about, by group."""
    places: dict[str, tuple[str, ...]] = {}
    if group_ids:
        for group_id, point_id in db.execute(
            select(ChatGroupPoint.group_id, ChatGroupPoint.point_id).where(ChatGroupPoint.group_id.in_(group_ids))
        ).all():
            places[group_id] = (*places.get(group_id, ()), point_id)
    return places


def _apply_rules(rules: list[MessageRule], row: dict, chat: str, map_id: str) -> list[Outcome]:
    """
    What the rules do with a message, written on its row: what to highlight
    (what every rule it meets looks for), and dismissed when one of them hides it.
    """
    try:
        found = outcomes(rules, row["text"], chat)
    except (KeyError, TypeError, AttributeError) as error:
        # A rule that cannot be read must not keep the messages from being kept
        logger.warning(f"Rules of map '{map_id}' skipped on a group message: {type(error).__name__}")
        return []
    highlights = list(dict.fromkeys(word for rule in found for word in rule.highlights))
    row["highlights"] = highlights or None
    if any(rule.hide for rule in found):
        row.update(dismissed_at=datetime.now(UTC), dismissed_by_rule=True)
    return found


def _from_lines(lines: list[vocabulary.Suggestion]) -> list[dict]:
    return [
        {
            "line": item.line, "point_id": item.point_id, "key_id": item.key_id, "value_id": item.value_id,
            "words": list(item.words), "doubt": item.doubt, "rule_id": None, "rule": None,
        }
        for item in lines
    ]


def _from_rules(
    found: list[Outcome], points: set, values: set, lines: list[vocabulary.Suggestion],
    group_places: tuple[str, ...], question: bool,
) -> list[dict]:
    """
    What the rules a message meets suggest, for the whole message: a value
    without a place goes to the place of its group when the group has only
    one; what a line already suggests for the place is not said again.
    """
    made: list[dict] = []
    for rule in found:
        point_id = rule.point_id if rule.point_id in points else None
        value_id = rule.value_id if rule.value_id in values else None
        key_id = rule.key_id if value_id else None
        if point_id is None and value_id and len(group_places) == 1:
            point_id = group_places[0]
        if not (point_id or value_id):
            continue
        if point_id and any(
            line.point_id == point_id and (value_id is None or (line.key_id, line.value_id) == (key_id, value_id))
            for line in lines
        ):
            continue
        made.append({
            "line": None, "point_id": point_id, "key_id": key_id, "value_id": value_id,
            "words": rule.highlights, "doubt": None, "rule_id": rule.rule_id, "rule": rule.rule,
        })
    for item in made:
        # Two rules giving one key of a place different values: a person chooses
        others = [
            other for other in made
            if other is not item and item["key_id"] and (other["point_id"], other["key_id"]) == (item["point_id"], item["key_id"])
            and other["value_id"] != item["value_id"]
        ]
        item["doubt"] = vocabulary.QUESTION if question else vocabulary.TWO_VALUES if others else None
    return made


def suggest(db, map_id: str, rows: list[dict], chat_of: dict[str, str]) -> dict[str, list[dict]]:
    """
    What the rules and the words of the map suggest for each message of a
    batch, by the id of the message: rows of message_suggestions, pending.
    Rows are messages as dictionaries ({id, group_id, text} and ROW_DEFAULTS);
    what the rules do to them (highlights, dismissed) is written on them.
    chat_of gives the pseudonym of the group of each message, by its id.
    """
    rules = rules_of(db, map_id)
    reader = _reader_of(db, map_id)
    if not rules and reader is None:
        return {}
    points, values = _still_there(db, map_id, rules) if rules else (set(), set())
    places = _group_places(db, {row["group_id"] for row in rows})
    known = languages()
    made: dict[str, list[dict]] = {}
    for row in rows:
        found = _apply_rules(rules, row, chat_of.get(row["id"], ""), map_id) if rules else []
        if row["dismissed_by_rule"]:
            continue
        group_places = places.get(row["group_id"], ())
        lines = vocabulary.read(reader, row["text"], group_places=group_places) if reader else []
        question = bool(found) and asks(row["text"] or "", vocabulary.tokens(row["text"] or ""), known)
        suggestions = _from_lines(lines) + _from_rules(found, points, values, lines, group_places, question)
        if suggestions:
            made[row["id"]] = [
                {**item, "id": str(uuid.uuid4()), "message_id": row["id"], "state": PENDING} for item in suggestions
            ]
    return made


def answer_on_link(db, message_id: str, point_id: str, key_id: str, value_id: str | None) -> bool:
    """
    What a message suggested, answered by a link of it to a place and a value
    of a key: a suggestion of that place (or without one) and that key (or
    without one) is confirmed when it gives what the link gives, and wrong when
    it gives another value. A suggestion of only the place is confirmed by any
    link to it. Whether a rule suggested what the link gives: the change is
    then the rule's; what the words of the map suggested is the message's.
    """
    pending = db.execute(
        select(MessageSuggestion).where(
            MessageSuggestion.message_id == message_id, MessageSuggestion.state == PENDING,
            or_(MessageSuggestion.point_id == point_id, MessageSuggestion.point_id.is_(None)),
            or_(MessageSuggestion.key_id == key_id, MessageSuggestion.key_id.is_(None)),
        )
    ).scalars().all()
    by_rule = False
    for suggestion in pending:
        right = suggestion.value_id is None or suggestion.value_id == value_id
        suggestion.state = ACCEPTED if right else REJECTED
        suggestion.answered_at = func.now()
        by_rule = by_rule or (right and suggestion.rule_id is not None)
    return by_rule


def values_now(db, pairs: set[tuple[str, str]]) -> dict[tuple[str, str], set[str]]:
    """The values each point has now for each key, of the pairs of point and key asked."""
    now: dict[tuple[str, str], set[str]] = {}
    if pairs:
        for point_id, key_id, value_id in db.execute(
            select(PointTag.point_id, PointTag.key_id, PointTag.value_id)
            .where(tuple_(PointTag.point_id, PointTag.key_id).in_(pairs))
        ).all():
            now.setdefault((point_id, key_id), set()).add(value_id)
    return now
