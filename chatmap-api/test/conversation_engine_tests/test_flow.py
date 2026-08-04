from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from conversation_engine.conversation import Conversation, ConversationKey
from conversation_engine.event import Event, EventName
from conversation_engine.flow import Flow, Flows, HelpFlow
from conversation_engine.tool import BotTool
from store.received_messages_store import ReceivedMessage


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


def _event(name: EventName) -> Event:
    return Event(name=name, occurred_at=datetime.now(timezone.utc))


class _FakeFlow:
    def __init__(self, events, check_tool_for_event):
        self._events = events
        self.check_tool_for_event = check_tool_for_event

    def expected_events(self):
        return self._events


# ---- Flow ----

async def test_check_tool_for_event_invokes_the_registered_tool():
    tool = AsyncMock()
    flow = Flow(
        bot_state_store=Mock(), message_to_send_store=Mock(), survey_responses_store=Mock(),
        tools_by_events={EventName.USER_SEND_TEXT: tool},
    )
    event = _event(EventName.USER_SEND_TEXT)
    message = _message()
    conversation = _conversation()

    await flow.check_tool_for_event(event=event, message=message, device="device-1", conversation=conversation)

    tool.assert_awaited_once_with(event, message, "device-1", conversation)


async def test_check_tool_for_event_does_nothing_when_no_tool_registered():
    tool = AsyncMock()
    flow = Flow(
        bot_state_store=Mock(), message_to_send_store=Mock(), survey_responses_store=Mock(),
        tools_by_events={EventName.USER_UPLOAD_PHOTO: tool},
    )
    event = _event(EventName.USER_SEND_TEXT)

    await flow.check_tool_for_event(
        event=event, message=_message(), device="device-1", conversation=_conversation()
    )

    tool.assert_not_awaited()


def test_expected_events_returns_the_tools_by_events_keys():
    flow = Flow(
        bot_state_store=Mock(), message_to_send_store=Mock(), survey_responses_store=Mock(),
        tools_by_events={EventName.USER_SEND_TEXT: AsyncMock(), EventName.USER_SEND_COORDINATES: AsyncMock()},
    )

    assert flow.expected_events() == {EventName.USER_SEND_TEXT, EventName.USER_SEND_COORDINATES}


# ---- HelpFlow ----

def test_help_flow_shares_a_single_bot_tool_across_its_events():
    help_flow = HelpFlow(bot_state_store=Mock(), message_to_send_store=Mock(), survey_responses_store=Mock())

    tools = help_flow.tools_by_events

    assert set(tools.keys()) == {
        EventName.USER_SEND_TEXT, EventName.USER_UPLOAD_PHOTO, EventName.USER_SEND_COORDINATES
    }
    shared_tool = tools[EventName.USER_SEND_TEXT]
    assert isinstance(shared_tool, BotTool)
    assert tools[EventName.USER_UPLOAD_PHOTO] is shared_tool
    assert tools[EventName.USER_SEND_COORDINATES] is shared_tool


# ---- Flows ----

def test_registered_flows_returns_a_help_flow_with_its_own_stores():
    flows = Flows(client=Mock())

    registered = flows.registered_flows()

    assert len(registered) == 1
    help_flow = registered[0]
    assert isinstance(help_flow, HelpFlow)
    assert help_flow.bot_state_store is flows.bot_state_store
    assert help_flow.message_to_send_store is flows.message_to_send_store


async def test_call_tools_for_dispatches_to_the_matching_flow():
    matching_tool_call = AsyncMock()
    other_tool_call = AsyncMock()
    matching_flow = _FakeFlow({EventName.USER_SEND_TEXT}, matching_tool_call)
    other_flow = _FakeFlow({EventName.USER_UPLOAD_PHOTO}, other_tool_call)
    flows = Flows(client=Mock())
    flows.registered_flows = lambda: [matching_flow, other_flow]
    event = _event(EventName.USER_SEND_TEXT)
    message = _message()
    conversation = _conversation()

    await flows.call_tools_for(event=event, message=message, device="device-1", conversation=conversation)

    matching_tool_call.assert_awaited_once_with(
        event=event, message=message, device="device-1", conversation=conversation
    )
    other_tool_call.assert_not_awaited()


async def test_call_tools_for_does_nothing_when_no_flow_expects_the_event():
    tool_call = AsyncMock()
    flow = _FakeFlow({EventName.USER_UPLOAD_PHOTO}, tool_call)
    flows = Flows(client=Mock())
    flows.registered_flows = lambda: [flow]
    event = _event(EventName.USER_SEND_TEXT)

    await flows.call_tools_for(
        event=event, message=_message(), device="device-1", conversation=_conversation()
    )

    tool_call.assert_not_awaited()
