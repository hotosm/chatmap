import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from bot.flow import BotFlowContext
from bot.flows.first_time_mapping.flow import FirstTimeMappingFlow
from conversation_engine.conversation import Conversation, ConversationKey
from conversation_engine.event import Event, EventName
from conversation_engine.tool import BotTool
from settings import CHATMAP_ENC_KEY
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore
from store.received_messages_store import ReceivedMessage
from store.survey_responses_store import SurveyResponsesStore


def _encrypt(plaintext: str) -> str:
    key = CHATMAP_ENC_KEY.encode("utf-8")
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    return base64.b64encode(nonce + ciphertext + tag).decode("utf-8")


def _message(**overrides) -> ReceivedMessage:
    fields = dict(
        id="1", receiver="receiver", sender="sender-1", chat="chat-1",
        sender_enc="sender-enc-1", chat_enc="chat-enc-1",
        text="", date="2026-07-14T12:00:00Z",
        location="", photo="", video="", audio="", file="",
    )
    fields.update(overrides)
    return ReceivedMessage(**fields)


def _conversation() -> Conversation:
    return Conversation(key=ConversationKey(sender="sender-1", chat="chat-1"))


def _make_bot_tool(
        bot_state_store=None,
        message_to_send_store=None,
        bot_consumed_messages_store=None,
        survey_responses_store=None
) -> BotTool:
    return BotTool(
        bot_state_store=bot_state_store or AsyncMock(spec=BotStateStore),
        message_to_send_store=message_to_send_store or AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=bot_consumed_messages_store or AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=survey_responses_store or AsyncMock(spec=SurveyResponsesStore),
    )


async def test_call_decrypts_text_and_delegates_to_the_flow():
    plaintext = "hola bot"
    message = _message(
        id="msg-1", text=_encrypt(plaintext), sender="sender-1", chat="chat-1", sender_enc="recipient-enc-1"
    )
    event = Event(name=EventName.USER_SEND_TEXT, occurred_at=datetime.now(timezone.utc))
    bot_state_store = AsyncMock(spec=BotStateStore)
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    survey_responses_store = AsyncMock(spec=SurveyResponsesStore)
    bot_tool = _make_bot_tool(
        bot_state_store, message_to_send_store, bot_consumed_messages_store, survey_responses_store
    )
    fake_flow = AsyncMock()

    with patch.object(FirstTimeMappingFlow, "create", AsyncMock(return_value=fake_flow)) as mock_create:
        await bot_tool(event=event, message=message, device="device-1", conversation=_conversation())

    expected_key = f"bot_state:{FirstTimeMappingFlow.name}:sender-1chat-1"
    mock_create.assert_awaited_once_with(
        bot_state_key=expected_key,
        bot_state_store=bot_state_store,
        message_to_send_store=message_to_send_store,
        bot_consumed_messages_store=bot_consumed_messages_store,
        survey_responses_store=survey_responses_store,
    )
    fake_flow.call.assert_awaited_once_with(
        current_event=EventName.USER_SEND_TEXT,
        context=BotFlowContext(
            state_key=expected_key, recipient="recipient-enc-1", sender="device-1", answer=plaintext,
            message_id="msg-1", occurred_at=event.occurred_at, point_id=None, bot_state_store=bot_state_store,
        ),
    )


async def test_call_sets_point_id_to_message_id_only_for_the_coordinates_event():
    message = _message(id="point-42", text="")
    event = Event(name=EventName.USER_SEND_COORDINATES, occurred_at=datetime.now(timezone.utc))
    bot_tool = _make_bot_tool()
    fake_flow = AsyncMock()

    with patch.object(FirstTimeMappingFlow, "create", AsyncMock(return_value=fake_flow)):
        await bot_tool(event=event, message=message, device="device-1", conversation=_conversation())

    assert fake_flow.call.await_args.kwargs["context"].point_id == "point-42"


@pytest.mark.parametrize("event_name", [n for n in EventName if n != EventName.USER_SEND_COORDINATES])
async def test_call_leaves_point_id_none_for_non_coordinates_events(event_name):
    message = _message(id="point-42", text="")
    event = Event(name=event_name, occurred_at=datetime.now(timezone.utc))
    bot_tool = _make_bot_tool()
    fake_flow = AsyncMock()

    with patch.object(FirstTimeMappingFlow, "create", AsyncMock(return_value=fake_flow)):
        await bot_tool(event=event, message=message, device="device-1", conversation=_conversation())

    assert fake_flow.call.await_args.kwargs["context"].point_id is None


async def test_call_passes_through_empty_text_without_decrypting():
    message = _message(text="")
    event = Event(name=EventName.USER_SEND_TEXT, occurred_at=datetime.now(timezone.utc))
    bot_tool = _make_bot_tool()
    fake_flow = AsyncMock()

    with patch.object(FirstTimeMappingFlow, "create", AsyncMock(return_value=fake_flow)):
        await bot_tool(event=event, message=message, device="device-1", conversation=_conversation())

    fake_flow.call.assert_awaited_once()
    assert fake_flow.call.await_args.kwargs["context"].answer == ""


@pytest.mark.parametrize("event_name", list(EventName))
async def test_call_passes_the_triggering_event_name_through_unchanged(event_name):
    message = _message(text=_encrypt("hi"))
    event = Event(name=event_name, occurred_at=datetime.now(timezone.utc))
    bot_tool = _make_bot_tool()
    fake_flow = AsyncMock()

    with patch.object(FirstTimeMappingFlow, "create", AsyncMock(return_value=fake_flow)):
        await bot_tool(event=event, message=message, device="device-1", conversation=_conversation())

    assert fake_flow.call.await_args.kwargs["current_event"] == event_name
