from abc import ABC, abstractmethod
from conversation_engine.event import EventName
from dataclasses import dataclass
from enum import Enum
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


class BotFlow(ABC):
    def __init__(self,
                 state: Enum,
                 language: Language,
                 bot_state_store: BotStateStore,
                 message_to_send_store: MessageToSendStore
                 ):
        self.state = state
        self.language = language
        self.bot_state_store = bot_state_store
        self.message_to_send_store = message_to_send_store

    @classmethod
    @abstractmethod
    async def create(
            cls,
            bot_state_key: str,
            bot_state_store: BotStateStore,
            message_to_send_store: MessageToSendStore
    ):
        ...


def not_handler_created(flow_name: str, state: Enum, event: EventName):
    logger.error(f"Flow: '{flow_name}' with state: '{state}' receive the event: '{event}' and hasn't a handler defined")


BotHandler = Callable[[BotFlow, BotFlowContext], Awaitable[None]]
BotTransitions = dict[tuple[Enum, EventName], BotHandler]
