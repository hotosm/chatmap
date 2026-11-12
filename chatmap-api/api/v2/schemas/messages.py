from datetime import datetime
from typing import Literal

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


class LineSuggestion(BaseModel):
    """
    What a message suggests: a place, a value of a key, or both. From the
    words of the map, for a line (`line` counts from 0); from a rule, for the
    whole message (`line` None, `rule` the description the rule had). `words`
    are the ones that made it, as the message writes them, to highlight them.
    `doubt` says why a person should look at it closely ("question": it asks;
    "two_values": it gives one key of the place two values); None when it is
    plain. `unchanged`: the place has that value now, so confirming it renews
    it. Pending until a person confirms it (linking the message as it says, or
    renewing it) or says no.
    """
    id: str
    line: int | None = None
    point_id: str | None = None
    key_id: str | None = None
    value_id: str | None = None
    rule: str | None = None
    words: list[str] = []
    doubt: Literal["question", "two_values"] | None = None
    state: Literal["pending", "accepted", "rejected"]
    unchanged: bool = False


# How many suggestions are renewed at once: a bulletin has about one per place of the map
MAX_RENEWED = 500


class RenewRequest(BaseModel):
    """The suggestions of a message a person chose to renew: the ones whose points still have what they say."""
    suggestion_ids: list[str] = Field(min_length=1, max_length=MAX_RENEWED)


class MessageSuggestions(BaseModel):
    """
    The suggestions of a message after an answer; `links`: the ones a renewal
    made (a change of each point renewed, from the message), newest first.
    """
    message_id: str
    suggestions: list[LineSuggestion] = []
    links: list[MessageLink] = []


class SuggestionAnswer(BaseModel):
    """No to what a message suggests (rejected), or that taken back."""
    rejected: bool


class GroupMessageItem(BaseModel):
    """
    A message of a chat group the map listens to. `group_id` and `sender`
    are pseudonyms: the same group or person always has the same one within
    a map. `location` is "latitude,longitude". `links`: the values it gave
    to points, newest first. `rank`: where it goes in a read in two
    stretches (all of them, or the new ones): 2 sent after the last message
    reviewed in its group and marked by a rule, 1 sent after it, 0 before
    it; None in the other reads and outside of them.
    """
    id: str
    group_id: str
    sender: str
    text: str
    location: str | None
    sent_at: datetime
    dismissed_at: datetime | None = None
    # Dismissed by a rule that hides it, not by a person
    dismissed_by_rule: bool = False
    links: list[MessageLink] = []
    # What the rules it meets look for that it says, to highlight it
    highlights: list[str] = []
    # What it suggests: the whole message first (rules), then in the order of its lines (words)
    suggestions: list[LineSuggestion] = []
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
    # The suggestions of the message after it: the link answers the ones for its point and key
    suggestions: list[LineSuggestion] = []


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
