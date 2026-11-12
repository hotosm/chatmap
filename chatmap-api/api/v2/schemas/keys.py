import re

from pydantic import BaseModel, field_validator, model_validator

# A color is a hex color like #D73F3F
COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
MAX_KEYS = 10
MAX_KEY_NAME_LENGTH = 40
MAX_KEY_VALUES = 30
MAX_LIST_VALUE_LENGTH = 40
MAX_VALUE_DESCRIPTION_LENGTH = 200
# An option lasts up to 30 days without being confirmed
MAX_EXPIRES_AFTER_HOURS = 720


class KeyValueItem(BaseModel):
    """
    A value of a key with a list (an option, on screen), like "Closed" for a
    status. One without id is new; the id of an existing one is kept across
    edits because points refer to it. An archived value cannot be given, but
    the points having it keep it. Its color is optional: without one it shows
    gray. A point nobody confirmed for expires_after hours shows as unknown;
    None: it does not expire.
    """
    id: str | None = None
    value: str
    description: str = ""
    color: str | None = None
    expires_after: int | None = None
    archived: bool = False

    @field_validator("value")
    @classmethod
    def check_value(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= MAX_LIST_VALUE_LENGTH:
            raise ValueError(f"a value needs between 1 and {MAX_LIST_VALUE_LENGTH} characters")
        return value

    @field_validator("description")
    @classmethod
    def check_description(cls, description: str) -> str:
        description = description.strip()
        if len(description) > MAX_VALUE_DESCRIPTION_LENGTH:
            raise ValueError(f"a value description takes up to {MAX_VALUE_DESCRIPTION_LENGTH} characters")
        return description

    @field_validator("color")
    @classmethod
    def check_color(cls, color: str | None) -> str | None:
        if color is None:
            return None
        if not COLOR.fullmatch(color):
            raise ValueError("a color must be a hex color like #D73F3F")
        return color.upper()

    @field_validator("expires_after")
    @classmethod
    def check_expires_after(cls, hours: int | None) -> int | None:
        if hours is not None and not 1 <= hours <= MAX_EXPIRES_AFTER_HOURS:
            raise ValueError(f"a value expires after between 1 and {MAX_EXPIRES_AFTER_HOURS} hours")
        return hours


def _check_values(values: list[KeyValueItem] | None):
    if values is None:
        return
    if len([value for value in values if not value.archived]) > MAX_KEY_VALUES:
        raise ValueError(f"a key takes up to {MAX_KEY_VALUES} values, not counting the archived ones")
    texts = [value.value.lower() for value in values]
    if len(texts) != len(set(texts)):
        raise ValueError("every value of a key needs to be different")


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
    of its values: one left out is removed, if no point has it.
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
    """A key of a map with its values."""
    id: str
    key: str
    single: bool
    closed: bool
    colors_map: bool
    archived: bool
    values: list[KeyValueItem] = []


class MapKeysResponse(BaseModel):
    keys: list[KeyItem] = []
