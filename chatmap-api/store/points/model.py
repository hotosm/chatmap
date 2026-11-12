import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import Index, text

from db import Point

Index(
    "ix_points_contributor_id_time_id",
    Point.contributor_id,
    Point.time,
    Point.id,
    postgresql_where=text("contributor_id IS NOT NULL"),
)


def point_id_of(sender: str, map_id: str, latitude: float, longitude: float, time: datetime,
                message: str | None) -> str:
    data = json.dumps(
        [sender, map_id, as_utc(time).isoformat(timespec="microseconds"), latitude, longitude, message or None],
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(data.encode()).hexdigest()


def as_utc(time: datetime) -> datetime:
    return time.astimezone(timezone.utc).replace(tzinfo=None)
