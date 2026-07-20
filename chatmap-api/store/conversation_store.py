import logging

from conversation_engine.conversation import Conversation, ConversationKey
from conversation_engine.event import Event, EventName
from datetime import datetime, timedelta
from redis import asyncio as async_redis

logger = logging.getLogger(__name__)


class ConversationStore:

    def __init__(self, client: async_redis.client.Redis):
        self.client = client

    async def add_event(self, key: ConversationKey, event: Event) -> None:
        timestamp = event.occurred_at.timestamp()
        await self.client.zadd(name=key.to_string(), mapping={event.key(): timestamp})

    async def load(self, key: ConversationKey, target_time: datetime, window_time: timedelta) -> Conversation:
        x_time_before = (target_time - window_time).timestamp()
        x_time_after = (target_time + window_time).timestamp()

        entries = await self.client.zrangebyscore(
            key.to_string(), x_time_before,
            x_time_after
        )

        events = []
        events_viewed = set()

        for entry in entries:
            timestamp, event_name = entry.split(":")
            timestamp = float(timestamp)
            occurred_at = datetime.fromtimestamp(timestamp)

            events.append(Event(name=EventName(event_name), occurred_at=occurred_at))
            events_viewed.add(event_name)

        return Conversation(key=key, log=events, events_viewed=events_viewed)
