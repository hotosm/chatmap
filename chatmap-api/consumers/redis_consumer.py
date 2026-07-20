from redis import asyncio
from events.message_event import MessageEvent


# TODO add documentation for class methods

class RedisConsumer:
    def __init__(self, redis_client: asyncio.Redis, stream_key: str, group_name: str, consumer_name: str):
        self.client = redis_client
        self.stream_key = stream_key
        self.group_name = group_name
        self.consumer_name = consumer_name

    def stream_name(self, device) -> str:
        return f"{self.stream_key}:{device}"

    async def get_messages_for(self, device) -> list[MessageEvent]:

        result = await self.client.xreadgroup(
            groupname=self.group_name,
            consumername=self.consumer_name,
            streams={self.stream_name(device): ">"}
        )

        messages = []

        for stream_name, entries in result:
            for entry_id, fields in entries:
                messages.append(MessageEvent.from_dict({**fields, "id": entry_id}))

        return messages

    async def ack_events(self, ids) -> None:
        """Acknowledge entries after successful processing"""
        raise "unimplemented"

    async def create_group(self, device):
        # id can be 0 (reprocess all events) or $ (only new events from now on)
        event_id_to_start = 0
        try:
            await self.client.xgroup_create(
                name=self.stream_name(device),
                groupname=self.group_name,
                id=event_id_to_start,
                mkstream=True
            )
        except asyncio.ResponseError as error:
            if "BUSYGROUP" not in str(error):
                # TODO: should log this error?
                raise error
