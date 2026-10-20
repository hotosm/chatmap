from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, field_validator

MAX_FREE_VALUE_LENGTH = 100
# How far ahead the clock of who sends a change can be
MAX_CLOCK_SKEW = timedelta(minutes=5)


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


class TagChangeRequest(BaseModel):
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
        if happened_at is None:
            return None
        # A time without zone is taken as UTC
        if happened_at.tzinfo is None:
            happened_at = happened_at.replace(tzinfo=UTC)
        # A clock ahead would make a change win over the ones that come later
        if happened_at > datetime.now(UTC) + MAX_CLOCK_SKEW:
            raise ValueError("a change cannot happen in a time to come")
        return happened_at


class PointKeyTags(BaseModel):
    """What a point has for a key after a change."""
    tags: list[PointTagItem] = []


class TagChangeItem(BaseModel):
    """
    One change of a tag of a point, or its confirmation: what was set or
    removed, when it happened, when it was written down, how and by whom.
    value is the name the value had then. An undone change stays, marked.
    """
    id: int
    key: str
    action: str
    value_id: str | None
    value: str | None
    happened_at: datetime
    recorded_at: datetime
    source: str
    user_id: str | None
    undone_at: datetime | None
    undone_by: str | None


class TagHistoryResponse(BaseModel):
    """The changes of the tags of a point, newest first."""
    changes: list[TagChangeItem] = []
