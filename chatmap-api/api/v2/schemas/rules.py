from typing import Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from recognition.rules import CONTAINS, CONTENT, GROUP, IS, IS_NOT, NOT_CONTAINS

MAX_RULES = 50
# In a group, and in a whole rule
MAX_CONDITIONS = 10
MAX_RULE_CONDITIONS = 20
MAX_CONDITION_VALUES = 10
MAX_CONDITION_LENGTH = 100
# What each field of a condition can say
OPERATORS = {CONTENT: (CONTAINS, NOT_CONTAINS), GROUP: (IS, IS_NOT)}
MAX_RULE_DESCRIPTION_LENGTH = 100


class RuleCondition(BaseModel):
    """
    One thing a message has to have, or not: a text it says (content, without
    minding case nor accents: contains any of the values, or none of them),
    or the group it comes from (group, by the id the groups of the map have:
    is one of the values, or none of them).
    """
    field: Literal[CONTENT, GROUP]
    operator: Literal[CONTAINS, NOT_CONTAINS, IS, IS_NOT]
    values: list[str] = Field(min_length=1, max_length=MAX_CONDITION_VALUES)

    @field_validator("values")
    @classmethod
    def check_values(cls, values: list[str]) -> list[str]:
        values = [value.strip() for value in values]
        if not all(1 <= len(value) <= MAX_CONDITION_LENGTH for value in values):
            raise ValueError(f"each value of a condition needs between 1 and {MAX_CONDITION_LENGTH} characters")
        # The same value twice says nothing more
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def check_operator(self) -> "RuleCondition":
        if self.operator not in OPERATORS[self.field]:
            raise ValueError(f"a {self.field} condition takes {' or '.join(OPERATORS[self.field])}")
        return self


class RuleGroup(BaseModel):
    """
    Conditions that go together: all of them, or any. The conditions of a
    rule are a group, which can hold groups of its own, one level down. Only
    the one of a whole rule can be empty: then its actions say when they apply.
    """
    match: Literal["all", "any"] = "all"
    items: list[Union[RuleCondition, "RuleGroup"]] = Field(max_length=MAX_CONDITIONS)


RuleGroup.model_rebuild()


def conditions_in(group: RuleGroup) -> list[RuleCondition]:
    """Every condition of a group, inside its groups too."""
    return [
        condition
        for item in group.items
        for condition in (conditions_in(item) if isinstance(item, RuleGroup) else [item])
    ]


def _check_group(group: RuleGroup, depth: int = 0) -> None:
    """A group holds groups only one level down, so a rule can still be read, and none of them is empty."""
    for item in group.items:
        if isinstance(item, RuleGroup):
            if depth > 0:
                raise ValueError("a group of conditions cannot hold groups")
            if not item.items:
                raise ValueError("a group of conditions needs a condition")
            _check_group(item, depth + 1)


class RuleAction(BaseModel):
    """
    What a rule does with a message that meets it: highlight what matched,
    suggest a place (point_id), suggest a value of a key with a list (key_id
    and value_id), or hide it (it is dismissed, marked by the rule). A
    suggestion can have conditions of its own, to suggest a place when the
    message names it, and a status when it says it.
    """
    type: Literal["highlight", "suggest_place", "suggest_status", "hide"]
    point_id: str | None = None
    key_id: str | None = None
    value_id: str | None = None
    conditions: RuleGroup | None = None

    @model_validator(mode="after")
    def check_what_it_needs(self) -> "RuleAction":
        needs = {
            "suggest_place": ("point_id",),
            "suggest_status": ("key_id", "value_id"),
        }.get(self.type, ())
        for name in ("point_id", "key_id", "value_id"):
            if (name in needs) != (getattr(self, name) is not None):
                raise ValueError(f"{self.type} {'needs' if name in needs else 'takes no'} {name}")
        if self.conditions is not None:
            if not needs:
                raise ValueError(f"{self.type} takes no conditions of its own")
            if not self.conditions.items:
                raise ValueError("the conditions of an action need a condition")
            _check_group(self.conditions, 1)
        return self


class RuleFields(BaseModel):
    """A rule as it is written: its conditions, in groups, and its actions, with conditions of their own or not."""
    description: str
    enabled: bool = True
    conditions: RuleGroup = Field(default_factory=lambda: RuleGroup(items=[]))
    actions: list[RuleAction] = Field(min_length=1, max_length=4)

    @field_validator("description")
    @classmethod
    def check_description(cls, description: str) -> str:
        description = description.strip()
        if not 1 <= len(description) <= MAX_RULE_DESCRIPTION_LENGTH:
            raise ValueError(f"a rule needs a description of 1 to {MAX_RULE_DESCRIPTION_LENGTH} characters")
        return description

    def every_condition(self) -> list[RuleCondition]:
        """The conditions of the rule and the ones of its actions."""
        return conditions_in(self.conditions) + [
            condition for action in self.actions if action.conditions for condition in conditions_in(action.conditions)
        ]

    @model_validator(mode="after")
    def check_conditions(self) -> "RuleFields":
        _check_group(self.conditions)
        # A rule without conditions anywhere would take every message
        if not self.conditions.items and not any(action.conditions for action in self.actions):
            raise ValueError("a rule needs a condition, of its own or of an action")
        if len(self.every_condition()) > MAX_RULE_CONDITIONS:
            raise ValueError(f"a rule takes up to {MAX_RULE_CONDITIONS} conditions")
        return self

    @model_validator(mode="after")
    def check_actions(self) -> "RuleFields":
        types = [action.type for action in self.actions]
        if len(set(types)) != len(types):
            raise ValueError("a rule does each action once")
        # A hidden message is not shown: nothing else of it would be seen
        if "hide" in types and len(types) > 1:
            raise ValueError("a rule that hides does nothing else")
        # What is highlighted is a text the message says
        if "highlight" in types and not any(condition.operator == CONTAINS for condition in self.every_condition()):
            raise ValueError("a rule highlights what a message says: it needs a condition on a text it contains")
        return self


class RuleItem(RuleFields):
    """A rule of a map."""
    id: str


class RulesResponse(BaseModel):
    """The rules of a map, oldest first. Every rule a message meets applies, in no order."""
    rules: list[RuleItem] = []
