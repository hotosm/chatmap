from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

SECRET_PATTERN = r"^[A-Za-z0-9_-]{43}$"


class JoinRequest(BaseModel):
    token: str = Field(min_length=1)
    nickname: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    secret: str = Field(pattern=SECRET_PATTERN)


class JoinResponse(BaseModel):
    contributor_id: str
    map_id: str
    map_name: str
