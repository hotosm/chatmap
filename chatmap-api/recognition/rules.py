"""
What the rules of a map do with a message. A rule has conditions (a text
the message says or not, the group it comes from or not), in groups of all
or any of them, and actions: highlight what matched, suggest a place,
suggest a value of a key, or hide the message. Every rule a message meets
applies; none decides for the others.
"""
from dataclasses import dataclass, field

from recognition.text import plain

CONTENT = "content"
GROUP = "group"
CONTAINS = "contains"
NOT_CONTAINS = "not_contains"
IS = "is"
IS_NOT = "is_not"
ALL = "all"
HIGHLIGHT = "highlight"
SUGGEST_PLACE = "suggest_place"
SUGGEST_STATUS = "suggest_status"
HIDE = "hide"


def _meets(condition: dict, text: str, group: str) -> bool:
    """Whether a message meets a condition: any of its values is there (or, negated, none of them)."""
    if condition["field"] == GROUP:
        found = group in condition["values"]
    else:
        found = any(plain(value) in text for value in condition["values"])
    return not found if condition["operator"] in (NOT_CONTAINS, IS_NOT) else found


def _holds(group: dict, text: str, group_id: str) -> bool:
    """Whether a message meets a group of conditions: all of them, or any, groups inside it too. No conditions are met."""
    if not group["items"]:
        return True
    results = (
        _holds(item, text, group_id) if "items" in item else _meets(item, text, group_id)
        for item in group["items"]
    )
    return all(results) if group["match"] == ALL else any(results)


def conditions_of(group: dict) -> list[dict]:
    """Every condition of a group, inside its groups too."""
    return [
        condition
        for item in group["items"]
        for condition in (conditions_of(item) if "items" in item else [item])
    ]


def every_condition(conditions: dict, actions: list[dict]) -> list[dict]:
    """The conditions of a rule and the ones of its actions."""
    return conditions_of(conditions) + [
        condition for action in actions if action.get("conditions")
        for condition in conditions_of(action["conditions"])
    ]


@dataclass
class Outcome:
    """What a rule a message meets does with it."""
    rule_id: str
    rule: str
    highlights: list[str] = field(default_factory=list)
    point_id: str | None = None
    key_id: str | None = None
    value_id: str | None = None
    hide: bool = False


def outcome_of(rule, said: str, group: str) -> Outcome | None:
    """
    What a rule does with a message (its text made plain, and the id of its
    group), or None when it does not match. A disabled rule does nothing. A
    rule matches when the message meets its conditions (none is met by all)
    and it does something: an action with conditions of its own only does
    what it does when the message meets them too. A rule that suggests a
    place with conditions of its own is about that place: when the message
    does not name it, the rule does not match. What is highlighted are the
    texts the rule, and its actions that apply, look for that the message says.
    """
    # A rule without conditions anywhere takes no message, rather than every one
    if not rule.enabled or not every_condition(rule.conditions, rule.actions) or not _holds(rule.conditions, said, group):
        return None
    actions = {
        action["type"]: action for action in rule.actions
        if not action.get("conditions") or _holds(action["conditions"], said, group)
    }
    highlights = [
        value
        for condition in every_condition(rule.conditions, list(actions.values())) if condition["operator"] == CONTAINS
        for value in condition["values"] if plain(value) in said
    ] if HIGHLIGHT in actions else []
    # Highlighting alone does something only when there is something to highlight
    if not (set(actions) - {HIGHLIGHT} or highlights):
        return None
    # A rule about a place says nothing of a message that does not name it
    if any(action["type"] == SUGGEST_PLACE for action in rule.actions) and SUGGEST_PLACE not in actions:
        return None
    place = actions.get(SUGGEST_PLACE) or {}
    status = actions.get(SUGGEST_STATUS) or {}
    return Outcome(
        rule_id=rule.id,
        rule=rule.description,
        highlights=list(dict.fromkeys(highlights)),
        point_id=place.get("point_id"),
        key_id=status.get("key_id"),
        value_id=status.get("value_id"),
        hide=HIDE in actions,
    )


def outcomes(rules: list, text: str, group: str) -> list[Outcome]:
    """What every rule a message meets does with it: they all apply, in no order, and none decides for the others."""
    said = plain(text or "")
    return [found for rule in rules if (found := outcome_of(rule, said, group)) is not None]
