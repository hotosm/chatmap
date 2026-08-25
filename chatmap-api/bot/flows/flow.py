from abc import ABC, abstractmethod

from bot.configured_messages import BotConfiguredMessages
from conversation_engine.event import EventName
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore
from store.survey_responses_store import SurveyResponsesStore
from typing import Callable, Awaitable

import logging

logger = logging.getLogger(__name__)


@dataclass
class BotFlowContext:
    state_key: str
    recipient: str
    sender: str
    answer: str
    message_id: str
    occurred_at: datetime
    point_id: str | None
    configured_messages: BotConfiguredMessages


class BotFlow(ABC):
    def __init__(self,
                 state: Enum,
                 bot_state_store: BotStateStore,
                 message_to_send_store: MessageToSendStore,
                 bot_consumed_messages_store: BotConsumedMessagesStore,
                 survey_responses_store: SurveyResponsesStore
                 ):
        self.state = state
        self.bot_state_store = bot_state_store
        self.message_to_send_store = message_to_send_store
        self.bot_consumed_messages_store = bot_consumed_messages_store
        self.survey_responses_store = survey_responses_store

    @classmethod
    @abstractmethod
    async def create(
            cls,
            bot_state_key: str,
            bot_state_store: BotStateStore,
            message_to_send_store: MessageToSendStore,
            bot_consumed_messages_store: BotConsumedMessagesStore,
            survey_responses_store: SurveyResponsesStore
    ):
        ...


def not_handler_created(flow_name: str, state: Enum, event: EventName):
    logger.error(f"Flow: '{flow_name}' with state: '{state}' receive the event: '{event}' and hasn't a handler defined")


BotHandler = Callable[[BotFlow, BotFlowContext], Awaitable[None]]
BotTransitions = dict[tuple[Enum, EventName], BotHandler]
