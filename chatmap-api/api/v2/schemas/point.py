from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field


class CreatePointRequest(BaseModel):
    id: UUID
    map_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    time: AwareDatetime
    message: str | None = None


class CreatePointResponse(BaseModel):
    id: str
