from abc import ABC, abstractmethod
from conversation_engine.event import EventName
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore
from typing import Callable, Awaitable

import logging

logger = logging.getLogger(__name__)


class Language(Enum):
    ES = "Español"
    EN = "English"
    PT = "Portugués"
    FR = "Francais"

    @classmethod
    def default(cls):
        return Language.ES


@dataclass
class BotFlowContext:
    state_key: str
    recipient: str
    sender: str
    answer: str
    message_id: str
    occurred_at: datetime


class BotFlow(ABC):
    def __init__(self,
                 state: Enum,
                 language: Language,
                 bot_state_store: BotStateStore,
                 message_to_send_store: MessageToSendStore,
                 bot_consumed_messages_store: BotConsumedMessagesStore
                 ):
        self.state = state
        self.language = language
        self.bot_state_store = bot_state_store
        self.message_to_send_store = message_to_send_store
        self.bot_consumed_messages_store = bot_consumed_messages_store

    @classmethod
    @abstractmethod
    async def create(
            cls,
            bot_state_key: str,
            bot_state_store: BotStateStore,
            message_to_send_store: MessageToSendStore,
            bot_consumed_messages_store: BotConsumedMessagesStore
    ):
        ...


def not_handler_created(flow_name: str, state: Enum, event: EventName):
    logger.error(f"Flow: '{flow_name}' with state: '{state}' receive the event: '{event}' and hasn't a handler defined")


BotHandler = Callable[[BotFlow, BotFlowContext], Awaitable[None]]
BotTransitions = dict[tuple[Enum, EventName], BotHandler]
