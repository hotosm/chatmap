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
    KeptDays,
    LinkRequest,
    LinkResponse,
    MessageChange,
    MessageLink,
    PhoneGroup,
)
from api.v2.routes.tags import _tag_item
from settings import SERVER_URL
from store.group_messages_store import GroupMessagesStore

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


def _group_item(group) -> ChatGroupItem:
    return ChatGroupItem(id=group.chat, name=group.name, enabled=group.enabled)


@router.get("/maps/{map_id}/groups")
async def read_groups(map_id: str, user: CurrentUser) -> ChatGroupsResponse:
    groups, kept_days = await call_store(GroupMessagesStore.groups(map_id, user.id, await _phone_groups(user.id)))
    return ChatGroupsResponse(groups=[_group_item(group) for group in groups], kept_days=kept_days)


@router.put("/maps/{map_id}/groups/{group_id}")
async def update_group(map_id: str, group_id: str, change: ChatGroupChange, user: CurrentUser) -> ChatGroupItem:
    # The phone is asked only to take the name of a group the map starts listening to
    phone_groups = await _phone_groups(user.id) if change.enabled else []
    group = await call_store(GroupMessagesStore.set_group(
        map_id, user.id, group_id, change.enabled, change.delete_messages, phone_groups,
    ))
    return _group_item(group)


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


def _message_item(message, chat: str, links=()) -> GroupMessageItem:
    return GroupMessageItem(
        id=message.id,
        group_id=chat,
        sender=message.sender,
        text=message.text,
        location=message.location,
        sent_at=message.sent_at,
        dismissed_at=message.dismissed_at,
        links=[_link_item(change) for change in links],
    )


@router.get("/maps/{map_id}/messages")
async def read_messages(
        map_id: str, user: CurrentUser, group_id: str | None = None,
        before: datetime | None = None, before_id: str | None = None,
        state: Literal["new", "linked", "dismissed"] | None = None,
) -> GroupMessagesResponse:
    """
    The next page goes after the last message of the previous one: its
    sent_at and id. Without `state`, the messages not dismissed.
    """
    if (before is None) != (before_id is None):
        raise HTTPException(status_code=422, detail="before and before_id go together.")
    # A time without zone is taken as UTC, as the messages give it
    if before is not None and before.tzinfo is None:
        before = before.replace(tzinfo=UTC)
    cursor = (before, before_id) if before is not None else None
    rows, links = await call_store(GroupMessagesStore.messages(map_id, user.id, group_id, cursor, state))
    return GroupMessagesResponse(messages=[
        _message_item(message, chat, links.get(message.id, [])) for message, chat in rows
    ])


@router.post("/messages/{message_id}/links")
async def link_message(message_id: str, link: LinkRequest, user: CurrentUser) -> LinkResponse:
    change, tags, applied = await call_store(GroupMessagesStore.link(
        message_id, user.id, link.point_id, link.key_id, value_id=link.value_id, value=link.value,
    ))
    return LinkResponse(link=_link_item(change), tags=[_tag_item(tag) for tag in tags], applied=applied)


@router.put("/messages/{message_id}")
async def update_message(message_id: str, change: MessageChange, user: CurrentUser) -> GroupMessageItem:
    """Dismiss a message or bring it back."""
    message, chat, links = await call_store(GroupMessagesStore.set_dismissed(message_id, user.id, change.dismissed))
    return _message_item(message, chat, links)
