from abc import ABC, abstractmethod
from redis import asyncio
from datetime import datetime, timezone
from events.message_event import MessageEvent


# TODO add documentation for class methods

class RedisConsumer(ABC):
    def __init__(self, redis_client: asyncio.Redis, stream_name: str, group_name: str, consumer_name: str):
        self.client = redis_client
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name

    async def list_entries(self) -> list[MessageEvent]:
        """Read all entries in the stream without consuming them (no group/ack involved)"""
        entries = await self.client.xrange(self.stream_name)
        return [MessageEvent.from_dict(data) for (_id, data) in entries]

    async def ack_events(self, ids) -> None:
        """Acknowledge entries after successful processing"""
        await self.client.xack(self.stream_name, self.group_name, ids)

    async def create_group(self):
        # id can be 0 (reprocess all events) or $ (only new events from now on)
        event_id_to_start = 0
        try:
            await self.client.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id=event_id_to_start,
                mkstream=True
            )
        except asyncio.ResponseError as error:
            if "BUSYGROUP" not in str(error):
                # TODO: should log this error?
                raise error
