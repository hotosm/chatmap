import base64
import json
from datetime import datetime

from results.error import InvalidCursor


def encode_cursor(time: datetime, point_id: str) -> str:
    data = json.dumps([time.isoformat(timespec="microseconds"), point_id], separators=(",", ":"))

    return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        time, point_id = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))

        if not isinstance(time, str) or not isinstance(point_id, str):
            raise ValueError

        parsed = datetime.fromisoformat(time)

        if parsed.tzinfo is not None:
            raise ValueError
    except (ValueError, TypeError):
        raise InvalidCursor

    return parsed, point_id
