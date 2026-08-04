import logging

from redis import RedisError
from redis.asyncio import ResponseError
from redis.client import Redis as RedisClient

from results.error import StoreUnavailable

logger = logging.getLogger(__name__)

from dataclasses import dataclass, fields


@dataclass
class ReceivedMessage:
    id: str
    receiver: str
    sender: str
    chat: str
    sender_enc: str
    chat_enc: str
    text: str
    date: str
    location: str
    photo: str
    video: str
    audio: str
    file: str

    # help to convert a key with a different name
    _aliases = {"from": "sender", "user": "receiver", "fromenc": "sender_enc", "chatenc": "chat_enc"}

    @classmethod
    def from_dict(cls, data: dict):
        normalized = {cls._aliases.get(k, k): v for k, v in data.items()}
        required_fields = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in normalized.items() if key in required_fields})

    def is_private_chat(self):
        return self.sender == self.chat


class ReceivedMessagesStore:
    def __init__(self, client: RedisClient):
        self.client = client
        self.stream_key = "messages"
        self.group_name = "received-messages-store-group"
        self.consumer_name = "received-messages-store-consumer"

    def _stream_name(self, device) -> str:
        return f"{self.stream_key}:{device}"

    async def setup_store_for(self, device) -> None:
        # id can be 0 (reprocess all events) or $ (only new events from now on)
        event_id_to_start = 0
        try:
            created = await self.client.xgroup_create(
                name=self._stream_name(device),
                groupname=self.group_name,
                id=event_id_to_start,
                mkstream=True
            )
            if created:
                logger.debug(f"Consumer group for device: '{device}' created")
            else:
                logger.warning(f"Creation consumer group for device: '{device}' failed")
        except ResponseError as error:
            # return BUSYGROUP when group already exists and this is not an error
            if "BUSYGROUP" not in str(error):
                raise StoreUnavailable

    async def _get_messages_for(self, device: str, new_messages: bool) -> list[ReceivedMessage]:
        try:
            await self.setup_store_for(device)

            result = await self.client.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self._stream_name(device): ">" if new_messages else "0"}
            )

            messages = []

            if not result:
                return messages

            for stream_name, entries in result:
                for entry_id, fields in entries:
                    if not fields:
                        logger.warning(
                            f"Pending message '{entry_id}' for device '{device}' has no data "
                            f"(likely trimmed from the stream); acking it without processing"
                        )
                        await self.mark_message_as_processed(message_id=entry_id, device=device)
                        continue
                    messages.append(ReceivedMessage.from_dict({**fields, "id": entry_id}))

            return messages
        except RedisError as error:
            logger.error(f"Fetch bot state failed with: '{error}'")
            raise StoreUnavailable

    async def get_new_messages_for(self, device: str) -> list[ReceivedMessage]:
        return await self._get_messages_for(device=device, new_messages=True)

    async def get_pending_messages_for(self, device: str) -> list[ReceivedMessage]:
        return await self._get_messages_for(device=device, new_messages=False)

    async def prune_pending_messages_for(self, device: str) -> None:
        try:
            pending = await self.client.xpending_range(
                name=self._stream_name(device=device),
                groupname=self.group_name,
                min="-",
                max="+",
                count=50
            )

            retry_times = 2

            to_delete = [p["message_id"] for p in pending if p["times_delivered"] >= retry_times]

            if len(pending) > 0:
                logger.info(f"Exist {len(to_delete)} messages with {retry_times} retries, we're going to delete them")

                await self.mark_message_as_processed(message_id=to_delete, device=device)

        except RedisError as error:
            logger.error(f"Fetch bot state failed with: '{error}'")
            raise StoreUnavailable

    async def mark_message_as_processed(self, message_id: str | list[str], device: str) -> None:
        ids = [message_id] if isinstance(message_id, str) else message_id
        if not ids:
            return
        try:
            await self.client.xack(
                self._stream_name(device=device),
                self.group_name,
                *ids
            )
        except RedisError as error:
            logger.error(f"Mark message with id: '{ids}' failed with: '{error}'")
            raise StoreUnavailable
