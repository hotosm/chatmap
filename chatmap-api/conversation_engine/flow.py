from abc import ABC

from conversation_engine.tool import BotTool, LogTool
from conversation_engine.conversation import Conversation
from conversation_engine.event import Event, EventName
from datetime import timedelta
from typing import ClassVar, Callable, Awaitable, Optional

from events.message_event import MessageEvent

Tool = Callable[[Event, MessageEvent, str], Awaitable[None]]


class Flow(ABC):
    name: str
    window_time: ClassVar[timedelta]

    def __init__(self, tools_by_events: Optional[dict[EventName, Tool]] = None):
        self.tools_by_events = tools_by_events if tools_by_events is not None else self.default_tools_by_events()

    @classmethod
    def default_tools_by_events(cls) -> dict[EventName, Tool]:
        raise NotImplementedError

    async def check_tool_for_event(self, event: Event, message: MessageEvent, device: str) -> None:
        tool = self.tools_by_events[event.name]
        await tool(event, message, device)

    async def check_end_flow(self, conversation: Conversation) -> None:
        expected_events = set(self.tools_by_events.keys())

        if expected_events <= conversation.events_viewed:
            LogTool()(data={"log_message": "all events in the %s flow occurred", "log_arg": self.name})


class LinkConversationFlow(Flow):
    name = "link_conversation"
    window_time = timedelta(minutes=2)

    @classmethod
    def default_tools_by_events(cls) -> dict[EventName, Tool]:
        bot_tool = BotTool()
        return {
            EventName.USER_UPLOAD_PHOTO: bot_tool,
            EventName.USER_SEND_COORDINATES: bot_tool,
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
