import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey

from db import Base

# Accepted file extensions and the content type each one is served with
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".opus": "audio/opus",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
}


class Media(Base):
    __tablename__ = "media"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    point_id = Column(String, ForeignKey("points.id", ondelete="CASCADE"), nullable=False, unique=True)
    storage_key = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    # When the user attached it in the app, in UTC. NULL for media uploaded before it was recorded
    captured_at = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), default=datetime.now, nullable=False)
