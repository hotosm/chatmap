from pydantic import BaseModel


class MediaResponse(BaseModel):
    id: str
    url: str
    content_type: str
    size: int
