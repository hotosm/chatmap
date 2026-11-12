import logging
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from hotosm_auth_fastapi import CurrentUser
from pydantic import TypeAdapter, ValidationError

from api.v2.errors import call_store
from api.v2.schemas.messages import (
    ChatGroupChange,
    ChatGroupItem,
    ChatGroupsResponse,
    GroupMessageItem,
    GroupMessagesResponse,
    GroupPlaces,
    KeptDays,
    LineSuggestion,
    LinkRequest,
    LinkResponse,
    MessageChange,
    MessageLink,
    MessageSuggestions,
    PhoneGroup,
    RenewRequest,
    SuggestionAnswer,
)
from api.v2.routes.tags import _tag_item
from settings import SERVER_URL
from store.group_messages_store import BY_REVIEW, GroupMessagesStore
from store.message_suggestions_store import MessageSuggestionsStore

router = APIRouter()
logger = logging.getLogger(__name__)

# The list of groups of a phone is read up to this size, so a bad answer cannot fill the memory
MAX_PHONE_GROUPS_BYTES = 1024 * 1024


class _TooLong(Exception):
    pass


async def _phone_groups(session: str) -> list[dict]:
    """The chat groups of the phone linked to a session, as the connector lists them: [{chat, name}]."""
    try:
        async with (
            httpx.AsyncClient() as client,
            client.stream("GET", f"{SERVER_URL}/groups", params={"session": session}) as response,
        ):
            response.raise_for_status()
            body = b""
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > MAX_PHONE_GROUPS_BYTES:
                    raise _TooLong
        groups = TypeAdapter(list[PhoneGroup]).validate_json(body)
    except (httpx.HTTPError, ValidationError, _TooLong) as error:
        logger.warning(f"Failed to list the chat groups of session '{session}': {type(error).__name__}")
        raise HTTPException(status_code=502, detail="Failed to list chat groups.")
    return [group.model_dump() for group in groups]


def _group_item(group, point_ids=()) -> ChatGroupItem:
    return ChatGroupItem(id=group.chat, name=group.name, enabled=group.enabled, point_ids=list(point_ids))


@router.get("/maps/{map_id}/groups")
async def read_groups(map_id: str, user: CurrentUser) -> ChatGroupsResponse:
    groups, places, kept_days = await call_store(
        GroupMessagesStore.groups(map_id, user.id, await _phone_groups(user.id))
    )
    return ChatGroupsResponse(
        groups=[_group_item(group, places.get(group.id, [])) for group in groups], kept_days=kept_days,
    )


@router.put("/maps/{map_id}/groups/{group_id}")
async def update_group(map_id: str, group_id: str, change: ChatGroupChange, user: CurrentUser) -> ChatGroupItem:
    # The phone is asked only to take the name of a group the map starts listening to
    phone_groups = await _phone_groups(user.id) if change.enabled else []
    group, point_ids = await call_store(GroupMessagesStore.set_group(
        map_id, user.id, group_id, change.enabled, change.delete_messages, phone_groups,
    ))
    return _group_item(group, point_ids)


@router.put("/maps/{map_id}/groups/{group_id}/points")
async def update_group_points(map_id: str, group_id: str, places: GroupPlaces, user: CurrentUser) -> ChatGroupItem:
    """
    The places a group is about, instead of the ones it had. Apart from
    update_group: enabling or disabling a group does more than this.
    """
    group, point_ids = await call_store(GroupMessagesStore.set_group_points(
        map_id, user.id, group_id, places.point_ids,
    ))
    # What its messages say without naming a place goes to the place of the group now
    await MessageSuggestionsStore.reread(map_id)
    return _group_item(group, point_ids)


@router.put("/maps/{map_id}/messages/kept-days")
async def update_kept_days(map_id: str, kept: KeptDays, user: CurrentUser) -> KeptDays:
    return KeptDays(days=await call_store(GroupMessagesStore.set_kept_days(map_id, user.id, kept.days)))


def _link_item(change) -> MessageLink:
    return MessageLink(
        change_id=change.id,
        point_id=change.point_id,
        key_id=change.key_id,
        value_id=change.value_id,
        value=change.value,
        undone=change.undone_at is not None,
    )


def _line_item(row, unchanged: bool) -> LineSuggestion:
    return LineSuggestion(
        id=row.id, line=row.line, point_id=row.point_id, key_id=row.key_id, value_id=row.value_id, rule=row.rule,
        words=list(row.words or []), doubt=row.doubt, state=row.state, unchanged=unchanged,
    )


async def _suggestions_of(user_id: str, message_ids: list[str]) -> dict[str, list[LineSuggestion]]:
    found = await call_store(MessageSuggestionsStore.suggestions(user_id, message_ids))
    return {message_id: [_line_item(row, unchanged) for row, unchanged in rows] for message_id, rows in found.items()}


def _message_item(message, chat: str, links=(), rank: int | None = None, suggestions=()) -> GroupMessageItem:
    return GroupMessageItem(
        id=message.id,
        group_id=chat,
        sender=message.sender,
        text=message.text,
        location=message.location,
        sent_at=message.sent_at,
        dismissed_at=message.dismissed_at,
        dismissed_by_rule=message.dismissed_by_rule,
        links=[_link_item(change) for change in links],
        highlights=message.highlights or [],
        suggestions=list(suggestions),
        rank=rank,
    )


def _utc(time: datetime | None) -> datetime | None:
    # A time without zone is taken as UTC, as the messages give it
    return time.replace(tzinfo=UTC) if time is not None and time.tzinfo is None else time


@router.get("/maps/{map_id}/messages")
async def read_messages(
        map_id: str, user: CurrentUser, group_id: str | None = None,
        before: datetime | None = None, before_id: str | None = None, before_rank: int | None = None,
        state: Literal["new", "linked", "dismissed", "suggested"] | None = None,
        as_of: datetime | None = None,
) -> GroupMessagesResponse:
    """
    The next page goes after the last message of the previous one: its
    sent_at and id, and its rank when the read goes in two stretches (all
    of them, or the new ones), with the as_of the first page gave. Without
    `state`, the messages not dismissed.
    """
    if (before is None) != (before_id is None):
        raise HTTPException(status_code=422, detail="before and before_id go together.")
    by_review = state in BY_REVIEW
    if before_rank is not None and not by_review:
        raise HTTPException(status_code=422, detail="before_rank goes only with all the messages or the new ones.")
    if by_review and (before is None) != (before_rank is None):
        raise HTTPException(status_code=422, detail="before, before_id and before_rank go together.")
    before = _utc(before)
    cursor = None
    if before is not None:
        cursor = (before_rank, before, before_id) if by_review else (before, before_id)
    rows, links, as_of = await call_store(
        GroupMessagesStore.messages(map_id, user.id, group_id, cursor, state, _utc(as_of))
    )
    suggestions = await _suggestions_of(user.id, [message.id for message, _, _ in rows])
    return GroupMessagesResponse(
        messages=[
            _message_item(message, chat, links.get(message.id, []), rank, suggestions.get(message.id, []))
            for message, chat, rank in rows
        ],
        as_of=as_of,
    )


@router.post("/messages/{message_id}/links")
async def link_message(message_id: str, link: LinkRequest, user: CurrentUser) -> LinkResponse:
    change, tags, applied = await call_store(GroupMessagesStore.link(
        message_id, user.id, link.point_id, link.key_id, value_id=link.value_id, value=link.value,
    ))
    suggestions = await _suggestions_of(user.id, [message_id])
    return LinkResponse(
        link=_link_item(change), tags=[_tag_item(tag) for tag in tags], applied=applied,
        suggestions=suggestions.get(message_id, []),
    )


@router.put("/messages/{message_id}")
async def update_message(message_id: str, change: MessageChange, user: CurrentUser) -> GroupMessageItem:
    """Dismiss a message or bring it back."""
    message, chat, links = await call_store(GroupMessagesStore.set_dismissed(message_id, user.id, change.dismissed))
    suggestions = await _suggestions_of(user.id, [message.id])
    return _message_item(message, chat, links, suggestions=suggestions.get(message.id, []))


@router.put("/suggestions/{suggestion_id}")
async def answer_line_suggestion(suggestion_id: str, answer: SuggestionAnswer, user: CurrentUser) -> MessageSuggestions:
    """
    No to what a message suggests, or that taken back. Yes is linking the
    message as it says, or renewing it.
    """
    message_id = await call_store(MessageSuggestionsStore.set_rejected(suggestion_id, user.id, answer.rejected))
    suggestions = await _suggestions_of(user.id, [message_id])
    return MessageSuggestions(message_id=message_id, suggestions=suggestions.get(message_id, []))


@router.post("/messages/{message_id}/suggestions/renew")
async def renew_suggestions(message_id: str, renewal: RenewRequest, user: CurrentUser) -> MessageSuggestions:
    """
    Confirms, with one click of a person, the suggestions of a message whose
    points still have what they say: they are said again at the time of the
    message. The ones whose point changed since stay pending.
    """
    changes = await call_store(MessageSuggestionsStore.renew(message_id, user.id, renewal.suggestion_ids))
    suggestions = await _suggestions_of(user.id, [message_id])
    return MessageSuggestions(
        message_id=message_id, suggestions=suggestions.get(message_id, []), links=[_link_item(change) for change in changes],
    )
