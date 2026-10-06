from datetime import datetime
from typing import List

from pydantic import BaseModel, field_validator, model_validator

# Colors a map status can be shown with
STATUS_COLORS = ("#3E9E47", "#D73F3F", "#E9A23B", "#2E4873", "#7A4FB5", "#9A969B")
MAX_STATUSES = 10
MAX_STATUS_NAME_LENGTH = 40
MAX_STATUS_DESCRIPTION_LENGTH = 200


class MapStatusItem(BaseModel):
    """
    One status the points of a map can have. A status without an id is a new
    one; the id of an existing status is preserved across edits because
    points refer to it.
    """
    id: str | None = None
    name: str
    description: str = ""
    color: str

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
        if color not in STATUS_COLORS:
            raise ValueError(f"a status color must be one of {', '.join(STATUS_COLORS)}")
        return color


class MapStatuses(BaseModel):
    """
    The whole list of statuses of a map, in the order they are shown.
    """
    statuses: List[MapStatusItem] = []

    @model_validator(mode="after")
    def check_statuses(self):
        if len(self.statuses) > MAX_STATUSES:
            raise ValueError(f"a map takes up to {MAX_STATUSES} statuses")
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
    statuses: List[MapStatusItem] = []
    points: List[PointStatusItem] = []
