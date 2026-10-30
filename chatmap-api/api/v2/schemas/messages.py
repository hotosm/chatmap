from datetime import datetime

from pydantic import BaseModel, Field

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
    to it and keeps its messages.
    """
    id: str
    name: str
    enabled: bool


class ChatGroupsResponse(BaseModel):
    """The groups of the phone, and how many days the map keeps their messages."""
    groups: list[ChatGroupItem] = []
    kept_days: int
    max_kept_days: int = MAX_KEPT_DAYS


class ChatGroupChange(BaseModel):
    """Listen to a group or stop; when stopping, its messages can go now instead of when they expire."""
    enabled: bool
    delete_messages: bool = False


class KeptDays(BaseModel):
    """How many days the map keeps the messages of its groups."""
    days: int = Field(ge=1, le=MAX_KEPT_DAYS)


class GroupMessageItem(BaseModel):
    """
    A message of a chat group the map listens to. `group_id` and `sender`
    are pseudonyms: the same group or person always has the same one within
    a map. `location` is "latitude,longitude".
    """
    id: str
    group_id: str
    sender: str
    text: str
    location: str | None
    sent_at: datetime


class GroupMessagesResponse(BaseModel):
    """The messages of the groups a map listens to, newest first."""
    messages: list[GroupMessageItem] = []
