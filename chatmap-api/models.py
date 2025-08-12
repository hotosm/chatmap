from typing import List, Union
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

'''
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "message": "Test 10jul",
        "chat": "DisasterResponse",
        "username": "5491126106584@s.whatsapp.net",
        "time": "2025-07-10 19:01:17-03:00",
        "location": "",
        "related": 1074,
        "id": 1073
      },
      "geometry": {
        "type": "Point",
        "coordinates": [
          -64.26295,
          -31.00589
        ]
      }
    }
  ]
}
'''

class GeometryType(Enum):
    MULTI_POLYGON = "MultiPolygon"
    POLYGON = "Polygon"
    POINT = "Point"

class Properties(BaseModel):
    message: str = ""
    username: str = ""
    chat: str = ""
    time: str = ""
    file: str = ""
    location: str = ""
    related: Union[int, str]
    id: Union[int, str]

class Geometries(BaseModel):
    type: GeometryType
    coordinates: List[float]

class ISOCodeResponse(BaseModel):
    id: str
    name: str
    geometries: Optional[Geometries]

class Feature(BaseModel):
    type: str
    properties: Properties
    geometry: Geometries

class GeoJson(BaseModel):
    type: str
    features: List[Feature]
