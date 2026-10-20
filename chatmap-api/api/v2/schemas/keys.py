from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from api.v2.schemas.statuses import STATUS_COLOR, MapStatusItem, happened_at_utc

MAX_KEYS = 10
MAX_KEY_NAME_LENGTH = 40
MAX_KEY_VALUES = 30
MAX_FREE_VALUE_LENGTH = 100


class KeyValueItem(MapStatusItem):
    """
    An option of a key with a list, like a status: its name, a description,
    and how long it lasts without being confirmed. Its color is optional:
    without one it shows gray.
    """
    color: str | None = None

    @field_validator("color")
    @classmethod
    def check_color(cls, color: str | None) -> str | None:
        if color is None:
            return None
        if not STATUS_COLOR.fullmatch(color):
            raise ValueError("a color must be a hex color like #D73F3F")
        return color.upper()


def _check_values(values: list[KeyValueItem] | None):
    if values is None:
        return
    if len([value for value in values if not value.archived]) > MAX_KEY_VALUES:
        raise ValueError(f"a key takes up to {MAX_KEY_VALUES} options, not counting the archived ones")
    names = [value.name.lower() for value in values]
    if len(names) != len(set(names)):
        raise ValueError("every option needs a different name")


def _check_name(name: str) -> str:
    name = name.strip()
    if not 1 <= len(name) <= MAX_KEY_NAME_LENGTH:
        raise ValueError(f"a key name needs between 1 and {MAX_KEY_NAME_LENGTH} characters")
    return name


class NewKey(BaseModel):
    """
    A key a map defines for its points, like "Fuel" or "Category": one value
    per point or many, picked from a list of options or written freely.
    """
    key: str
    single: bool = True
    closed: bool = True
    # The points of the map show its colors by default; the one that did stops
    colors_map: bool = False
    values: list[KeyValueItem] = []

    @field_validator("key")
    @classmethod
    def check_key(cls, name: str) -> str:
        return _check_name(name)

    @model_validator(mode="after")
    def check_values(self):
        _check_values(self.values)
        return self


class KeyChanges(BaseModel):
    """
    What changes in a key; what is left out stays. values is the whole list
    of its options: one left out is removed, if no point has it.
    """
    key: str | None = None
    archived: bool | None = None
    # True: the map is colored by this key by default; False: by none
    colors_map: bool | None = None
    values: list[KeyValueItem] | None = None

    @field_validator("key")
    @classmethod
    def check_key(cls, name: str | None) -> str | None:
        return None if name is None else _check_name(name)

    @model_validator(mode="after")
    def check_values(self):
        _check_values(self.values)
        return self


class KeyItem(BaseModel):
    """A key of a map with its options. A key of the system cannot be removed nor renamed."""
    id: str
    key: str
    single: bool
    closed: bool
    builtin: bool
    colors_map: bool
    archived: bool
    values: list[KeyValueItem] = []


class MapKeysResponse(BaseModel):
    keys: list[KeyItem] = []


class PointTagItem(BaseModel):
    """
    One value a point has for a key: an option of its list (value_id) or a
    text (value), since when, and the last time it was confirmed.
    """
    point_id: str
    key_id: str
    value_id: str | None
    value: str | None
    since: datetime
    confirmed_at: datetime


class MapTagsResponse(BaseModel):
    """What the points of a map have for its keys. Points without tags are left out."""
    tags: list[PointTagItem] = []


class PointTagChange(BaseModel):
    """
    A value to give a point (set; the same again confirms it) or to take
    out (remove). An option of the list goes by its id; a free value, as
    text. Taking out the value of a key with one value needs no value.
    happened_at is when it was so; by default, now.
    """
    action: Literal["set", "remove"] = "set"
    value_id: str | None = None
    value: str | None = None
    happened_at: datetime | None = None

    @field_validator("value")
    @classmethod
    def check_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not 1 <= len(value) <= MAX_FREE_VALUE_LENGTH:
            raise ValueError(f"a value needs between 1 and {MAX_FREE_VALUE_LENGTH} characters")
        return value

    @field_validator("happened_at")
    @classmethod
    def check_happened_at(cls, happened_at: datetime | None) -> datetime | None:
        return happened_at_utc(happened_at)


class PointKeyTags(BaseModel):
    """What a point has for a key after a change."""
    tags: list[PointTagItem] = []
