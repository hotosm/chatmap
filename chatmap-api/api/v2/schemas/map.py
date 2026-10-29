from typing import Literal

from pydantic import BaseModel


class MapResponse(BaseModel):
    map_id: str
    map_name: str | None
    role: Literal["owner", "contributor"]
    nickname: str | None


class MapsResponse(BaseModel):
    maps: list[MapResponse]
