from datetime import datetime

from pydantic import BaseModel


class TagChangeItem(BaseModel):
    """
    One change of a tag of a point, or its confirmation: what was set or
    removed, when it happened, when it was written down, how and by whom.
    value is the name the value had then. An undone change stays, marked.
    """
    id: int
    key: str
    action: str
    value_id: str | None
    value: str | None
    happened_at: datetime
    recorded_at: datetime
    source: str
    user_id: str | None
    undone_at: datetime | None
    undone_by: str | None


class TagHistoryResponse(BaseModel):
    """The changes of the tags of a point, newest first."""
    changes: list[TagChangeItem] = []
