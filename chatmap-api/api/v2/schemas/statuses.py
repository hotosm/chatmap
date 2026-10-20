import re
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, field_validator, model_validator

# A status color is a hex color like #D73F3F
STATUS_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
MAX_STATUSES = 10
MAX_STATUS_NAME_LENGTH = 40
MAX_STATUS_DESCRIPTION_LENGTH = 200
# A status lasts up to 30 days without being confirmed
MAX_EXPIRES_AFTER_HOURS = 720
# How far ahead the clock of who sends a change can be
MAX_CLOCK_SKEW = timedelta(minutes=5)


def happened_at_utc(happened_at: datetime | None) -> datetime | None:
    """When a change happened, in UTC: a time without zone is taken as UTC."""
    if happened_at is None:
        return None
    if happened_at.tzinfo is None:
        happened_at = happened_at.replace(tzinfo=UTC)
    # A clock ahead would make a change win over the ones that come later
    if happened_at > datetime.now(UTC) + MAX_CLOCK_SKEW:
        raise ValueError("a change cannot happen in a time to come")
    return happened_at


class MapStatusItem(BaseModel):
    """
    One status the points of a map can have. A status without an id is a new
    one; the id of an existing status is preserved across edits because
    points refer to it. An archived status cannot be given to a point, but
    the points having it keep it; when it was archived is only told, never
    taken. A point whose status nobody confirmed for expires_after hours
    shows as unknown; None: it does not expire.
    """
    id: str | None = None
    name: str
    description: str = ""
    color: str
    expires_after: int | None = None
    archived: bool = False
    archived_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def check_name(cls, name: str) -> str:
        name = name.strip()
        if not 1 <= len(name) <= MAX_STATUS_NAME_LENGTH:
            raise ValueError(f"a status name needs between 1 and {MAX_STATUS_NAME_LENGTH} characters")
        return name

    @field_validator("description")
    @classmethod
    def check_description(cls, description: str) -> str:
        description = description.strip()
        if len(description) > MAX_STATUS_DESCRIPTION_LENGTH:
            raise ValueError(f"a status description takes up to {MAX_STATUS_DESCRIPTION_LENGTH} characters")
        return description

    @field_validator("color")
    @classmethod
    def check_color(cls, color: str) -> str:
        if not STATUS_COLOR.fullmatch(color):
            raise ValueError("a status color must be a hex color like #D73F3F")
        return color.upper()

    @field_validator("expires_after")
    @classmethod
    def check_expires_after(cls, hours: int | None) -> int | None:
        if hours is not None and not 1 <= hours <= MAX_EXPIRES_AFTER_HOURS:
            raise ValueError(f"a status expires after between 1 and {MAX_EXPIRES_AFTER_HOURS} hours")
        return hours


class MapStatuses(BaseModel):
    """
    The whole list of statuses of a map, in the order they are shown. A
    status left out is removed, which is only possible when no point has it.
    """
    statuses: list[MapStatusItem] = []

    @model_validator(mode="after")
    def check_statuses(self):
        if len([status for status in self.statuses if not status.archived]) > MAX_STATUSES:
            raise ValueError(f"a map takes up to {MAX_STATUSES} statuses, not counting the archived ones")
        names = [status.name.lower() for status in self.statuses]
        if len(names) != len(set(names)):
            raise ValueError("every status needs a different name")
        return self


class PointStatus(BaseModel):
    """
    The status to give a point, the one it has to confirm it, or None to
    take it out. happened_at is when it was so (the time of a message); by
    default, now. What happened before the last change does not change the
    point, it only goes to its history.
    """
    status: str | None = None
    happened_at: datetime | None = None

    @field_validator("happened_at")
    @classmethod
    def check_happened_at(cls, happened_at: datetime | None) -> datetime | None:
        return happened_at_utc(happened_at)


class PointStatusResponse(BaseModel):
    """
    The status a point has: since when, and the last time it was confirmed.
    status_updated_at is confirmed_at, as before there was a history.
    """
    status: str | None
    since: datetime | None = None
    confirmed_at: datetime | None = None
    status_updated_at: datetime | None


class PointStatusItem(BaseModel):
    id: str
    status: str
    since: datetime
    confirmed_at: datetime
    status_updated_at: datetime


class MapStatusesResponse(BaseModel):
    """
    The statuses of a map and the status each of its points has. Points
    without a status are left out.
    """
    statuses: list[MapStatusItem] = []
    points: list[PointStatusItem] = []
