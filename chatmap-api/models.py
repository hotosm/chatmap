from typing import List, Union
from enum import Enum
from pydantic import BaseModel
from typing import List

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
    POINT = "Point"

class Properties(BaseModel):
    message: str = ""
    username: str = ""
    chat: str = ""
    time: str = ""
    file: str = ""
    location: str = ""
    id: Union[int, str]

class PointGeometry(BaseModel):
    type: GeometryType.POINT
    coordinates: List[float]

class Feature(BaseModel):
    type: str
    properties: Properties
    geometry: List[PointGeometry]

class GeoJson(BaseModel):
    type: str
    features: List[Feature]
