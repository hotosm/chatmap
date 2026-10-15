from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field

from api.v2.schemas.media import MediaResponse


class CreatePointRequest(BaseModel):
    map_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    time: AwareDatetime
    message: str | None = None


class CreatePointResponse(BaseModel):
    id: str


class HistoryPointResponse(BaseModel):
    id: str
    time: datetime
    latitude: float
    longitude: float
    message: str | None
    media: MediaResponse | None


class HistoryResponse(BaseModel):
    points: list[HistoryPointResponse]
    next: str | None
