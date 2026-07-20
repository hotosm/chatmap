from abc import ABC

from conversation_engine.tool import BotTool, LogTool
from conversation_engine.conversation import Conversation
from conversation_engine.event import Event, EventName
from datetime import timedelta
from typing import ClassVar, Callable, Awaitable

from events.message_event import MessageEvent


class Flow(ABC):
    name: str
    window_time: ClassVar[timedelta]
    tools_by_events: ClassVar[dict[EventName, Callable[[Event, MessageEvent, str], Awaitable[None]]]]

    async def check_tool_for_event(self, event: Event, message: MessageEvent, device: str) -> None:
        tool_call = self.tools_by_events[event.name]
        await tool_call(event, message, device)

    async def check_end_flow(self, conversation: Conversation) -> None:
        expected_events = set(self.tools_by_events.keys())

        if expected_events <= conversation.events_viewed:
            LogTool()(data={"log_message": "all events in the %s flow occurred", "log_arg": self.name})


class LinkConversationFlow(Flow):
    name = "link_conversation"
    window_time = timedelta(minutes=2)
    tools_by_events = {
        EventName.USER_UPLOAD_PHOTO: lambda event, msg, device: BotTool()(
            data={"to": msg.sender, "message": "photo received!", "device": device}),
        EventName.USER_SEND_COORDINATES: lambda event, msg, device: BotTool()(
            data={"to": msg.sender, "message": "coordinates received!", "device": device}),
    }


class Flows:
    @classmethod
    def registered_flows(cls) -> list[Flow]:
        return [LinkConversationFlow()]

    @classmethod
    async def call_tools_for(cls, event: Event, message: MessageEvent, device: str):
        for flow in cls.registered_flows():
            await flow.check_tool_for_event(event=event, message=message, device=device)

    @classmethod
    async def call_tools_in_end_flow(cls, conversation: Conversation):
        for flow in cls.registered_flows():
            await flow.check_end_flow(conversation=conversation)
