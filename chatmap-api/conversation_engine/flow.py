from abc import ABC

from conversation_engine.tool import BotTool, logger
from conversation_engine.conversation import Conversation
from conversation_engine.event import Event, EventName
from datetime import timedelta
from typing import ClassVar, Callable, Awaitable, Optional

from redis.client import Redis as RedisClient

from store.bot_state_store import BotStateStore

from store.message_to_send_store import MessageToSendStore
from store.received_messages_store import ReceivedMessagesStore, ReceivedMessage

Tool = Callable[[Event, ReceivedMessage, str, Conversation], Awaitable[None]]


class Flow(ABC):
    name: str
    window_time: ClassVar[timedelta]

    def __init__(self, bot_state_store: BotStateStore, message_to_send_store: MessageToSendStore,
                 tools_by_events: Optional[dict[EventName, Tool]] = None):
        self.bot_state_store = bot_state_store
        self.message_to_send_store = message_to_send_store
        self.tools_by_events = tools_by_events if tools_by_events is not None else self.default_tools_by_events()

    def expected_events(self) -> set[EventName]:
        return set(self.tools_by_events.keys())

    @classmethod
    def default_tools_by_events(cls) -> dict[EventName, Tool]:
        raise NotImplementedError

    async def check_tool_for_event(
            self,
            event: Event,
            message: ReceivedMessage,
            device: str,
            conversation: Conversation
    ) -> None:
        tool = self.tools_by_events.get(event.name)
        if tool:
            await tool(event, message, device, conversation)
        else:
            logger.error("No tool configured for event: %s", event.name)


class HelpFlow(Flow):
    name = "help"
    window_time = timedelta(minutes=2)

    def default_tools_by_events(self) -> dict[EventName, Tool]:
        bot_tool = BotTool(bot_state_store=self.bot_state_store, message_to_send_store=self.message_to_send_store)

        return {
            EventName.USER_SEND_TEXT: bot_tool,
            EventName.USER_UPLOAD_PHOTO: bot_tool,
            EventName.USER_SEND_COORDINATES: bot_tool,
        }


class Flows:
    def __init__(self, client: RedisClient):
        self.bot_state_store = BotStateStore(client)
        self.message_to_send_store = MessageToSendStore(client=client)
        self.received_messages_store = ReceivedMessagesStore(client=client)

    def registered_flows(self) -> list[Flow]:
        return [HelpFlow(bot_state_store=self.bot_state_store, message_to_send_store=self.message_to_send_store)]

    async def call_tools_for(self, event: Event, message: ReceivedMessage, device: str, conversation: Conversation):
        for flow in self.registered_flows():
            if event.name in flow.expected_events():
                await flow.check_tool_for_event(event=event, message=message, device=device, conversation=conversation)
