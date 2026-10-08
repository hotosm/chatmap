import re
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

# A status color is a hex color like #D73F3F
STATUS_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")
MAX_STATUSES = 10
MAX_STATUS_NAME_LENGTH = 40
MAX_STATUS_DESCRIPTION_LENGTH = 200


class MapStatusItem(BaseModel):
    """
    One status the points of a map can have. A status without an id is a new
    one; the id of an existing status is preserved across edits because
    points refer to it. An archived status cannot be given to a point, but
    the points having it keep it; when it was archived is only told, never
    taken.
    """
    id: str | None = None
    name: str
    description: str = ""
    color: str
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
    status: str | None = None


class PointStatusResponse(BaseModel):
    status: str | None
    status_updated_at: datetime | None


class PointStatusItem(BaseModel):
    id: str
    status: str
    status_updated_at: datetime | None


class MapStatusesResponse(BaseModel):
    """
    The statuses of a map and the status each of its points has. Points
    without a status are left out.
    """
    statuses: list[MapStatusItem] = []
    points: list[PointStatusItem] = []
