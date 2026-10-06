from datetime import datetime
from typing import List, Literal, Tuple

from pydantic import BaseModel

from api.v2.schemas.statuses import MapStatusItem


class SurveyAnswer(BaseModel):
    question: str
    answer: str


class PointGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: Tuple[float, float]  # GeoJSON is [lon, lat]


class PointProperties(BaseModel):
    id: str
    time: datetime
    message: str = ""
    file: str | None = None
    tags: str = ""
    removed: bool = False
    status: str | None = None
    status_updated_at: datetime | None = None
    survey: List[SurveyAnswer] = []


class PointFeature(BaseModel):
    type: Literal["Feature"]
    geometry: PointGeometry
    properties: PointProperties


class MapResponse(BaseModel):
    """
    A map as a GeoJSON FeatureCollection: what the v1 map carries, plus the
    statuses of the map and the status of each point.
    """
    id: str
    name: str
    description: str | None = None
    sharing: str
    owner: bool
    is_live: bool
    type: Literal["FeatureCollection"]
    statuses: List[MapStatusItem] = []
    features: List[PointFeature] = []
