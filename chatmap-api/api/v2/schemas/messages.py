from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from api.v2.schemas.tags import PointTagItem, free_value
from store.group_messages_store import MAX_KEPT_DAYS


class PhoneGroup(BaseModel):
    """A chat group as the connector lists it: the hash of its chat and its name."""
    # A sha256 in hex
    chat: str = Field(max_length=64)
    # WhatsApp takes up to 100 characters; there is room to spare
    name: str = Field(max_length=200)


class ChatGroupItem(BaseModel):
    """
    A chat group of the phone of a live map. `id` is a pseudonym: the same
    group always has the same one within a map. `enabled`: the map listens
    to it and keeps its messages. `point_ids`: the places it is about.
    """
    id: str
    name: str
    enabled: bool
    point_ids: list[str] = []


class ChatGroupsResponse(BaseModel):
    """The groups of the phone, and how many days the map keeps their messages."""
    groups: list[ChatGroupItem] = []
    kept_days: int
    max_kept_days: int = MAX_KEPT_DAYS


class ChatGroupChange(BaseModel):
    """Listen to a group or stop; when stopping, its messages can go now instead of when they expire."""
    enabled: bool
    delete_messages: bool = False


class GroupPlaces(BaseModel):
    """The places a group is about, instead of the ones it had: points of the map. An empty list leaves it without any."""
    point_ids: list[str]


class KeptDays(BaseModel):
    """How many days the map keeps the messages of its groups."""
    days: int = Field(ge=1, le=MAX_KEPT_DAYS)


class MessageLink(BaseModel):
    """
    A value of a key a message gave a point: the change of its tag it made
    (change_id, to undo it with /tag-changes/{id}/undo). `value` is the name
    the value had then. An undone link stays, marked.
    """
    change_id: int
    point_id: str
    key_id: str
    value_id: str | None
    value: str | None
    undone: bool


class GroupMessageItem(BaseModel):
    """
    A message of a chat group the map listens to. `group_id` and `sender`
    are pseudonyms: the same group or person always has the same one within
    a map. `location` is "latitude,longitude". `links`: the values it gave
    to points, newest first. `rank`: where it goes in a read in two
    stretches (all of them, or the new ones): 1 sent after the last message
    reviewed in its group, 0 before it; None in the other reads and outside
    of them.
    """
    id: str
    group_id: str
    sender: str
    text: str
    location: str | None
    sent_at: datetime
    dismissed_at: datetime | None = None
    links: list[MessageLink] = []
    rank: int | None = None


class LinkRequest(BaseModel):
    """
    A value of a key a message tells about a point: the id of an option for
    a key with a list, a text for one without. It takes the time of the message.
    """
    point_id: str
    key_id: str
    value_id: str | None = None
    value: str | None = None

    @field_validator("value")
    @classmethod
    def check_value(cls, value: str | None) -> str | None:
        return free_value(value)


class LinkResponse(BaseModel):
    """
    The link made, what the point has now for the key, and whether that is
    the value of the message (`applied`): a message older than what the
    point has only goes to its history.
    """
    link: MessageLink
    tags: list[PointTagItem] = []
    applied: bool


class MessageChange(BaseModel):
    """Dismiss a message, or bring it back."""
    dismissed: bool


class GroupMessagesResponse(BaseModel):
    """
    The messages of the groups a map listens to, in the order of the read,
    and the time what was reviewed is taken at: the next pages ask with it.
    """
    messages: list[GroupMessageItem] = []
    as_of: datetime
