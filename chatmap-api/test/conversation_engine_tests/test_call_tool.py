import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

from conversation_engine.event import Event, EventName
from conversation_engine.flow import LinkConversationFlow
from events.message_event import MessageEvent

MESSAGE = MessageEvent(
    id="1",
    receiver="receiver",
    sender="sender",
    chat="chat",
    text="text",
    date="2026-07-20T00:00:00",
    location="",
    photo="photo.jpg",
    video="",
    audio="",
    file="",
)


def test_photo_received_calls_bot_tool():
    mock_tool = AsyncMock()
    flow = LinkConversationFlow(tools_by_events={EventName.USER_UPLOAD_PHOTO: mock_tool})
    event = Event(name=EventName.USER_UPLOAD_PHOTO, occurred_at=datetime.now())

    asyncio.run(flow.check_tool_for_event(event=event, message=MESSAGE, device="device-1"))

    mock_tool.assert_awaited_once_with(event, MESSAGE, "device-1")


def test_coordinates_received_calls_bot_tool():
    mock_tool = AsyncMock()
    flow = LinkConversationFlow(tools_by_events={EventName.USER_SEND_COORDINATES: mock_tool})
    event = Event(name=EventName.USER_SEND_COORDINATES, occurred_at=datetime.now())

    asyncio.run(flow.check_tool_for_event(event=event, message=MESSAGE, device="device-1"))

    mock_tool.assert_awaited_once_with(event, MESSAGE, "device-1")
