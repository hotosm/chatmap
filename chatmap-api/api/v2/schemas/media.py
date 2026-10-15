from datetime import datetime

from pydantic import BaseModel


class MediaResponse(BaseModel):
    id: str
    url: str
    content_type: str
    size: int
    captured_at: datetime | None
