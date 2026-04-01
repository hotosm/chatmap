from typing import List, Literal, Tuple
from datetime import datetime

from pydantic import BaseModel


class FeatureGeometry(BaseModel):
    """
    Represents the geometry of a GeoJSON feature (Point).
    """
    type: Literal["Point"]
    coordinates: Tuple[float, float]  # GeoJSON is [lon, lat]


class FeatureProperties(BaseModel):
    """
    Represents the properties of a GeoJSON feature.
    """
    id: str
    time: datetime
    # username_id: str
    message: str | None = None
    file: str | None
    removed: bool = False
    tags: str = ""

class Feature(BaseModel):
    """
    Represents a GeoJSON feature.
    """
    type: Literal["Feature"]
    geometry: FeatureGeometry
    properties: FeatureProperties


class FeatureCollection(BaseModel):
    """
    Represents a GeoJSON FeatureCollection.
    """
    id: str
    sharing: str
    owner: bool
    name: str
    type: Literal["FeatureCollection"]
    centroid: str = ""
    features: List[Feature] = []

class SaveMapFeatureProperties(BaseModel):
    """
    Represents the properties of a GeoJSON feature.
    """
    time: datetime
    message: str | None = None
    file: str | None = None
    file_type: str | None = None
    username: str
    tags: str = ""
    removed: bool = False


class SaveMapFeature(BaseModel):
    type: Literal["Feature"]
    geometry: FeatureGeometry
    properties: SaveMapFeatureProperties


class SaveMapFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    name: str
    description: str | None = None
    features: List[SaveMapFeature]


class SaveMapResult(BaseModel):
    id: str
    name: str


class SaveMediaResponse(BaseModel):
    uri: str

class PointTags(BaseModel):
    tags: str = ""