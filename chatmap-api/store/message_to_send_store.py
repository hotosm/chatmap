import logging

from redis import RedisError
from redis.asyncio.client import Redis as RedisClient

from results.error import StoreUnavailable

logger = logging.getLogger(__name__)


class MessageToSendStore:
    def __init__(self, client: RedisClient):
        self.client = client
        self.stream_key = "to_send"

    def _stream_name(self, device) -> str:
        return f"{self.stream_key}:{device}"

    async def send_message(self, sender: str, to: str, message: str):
        entry = {
            "to": to,
            "text": message
        }

        try:
            created = await self.client.xadd(
                name=self._stream_name(device=sender),
                fields=entry
            )

            logger.debug(f"Message to send successfully created with stream id: '{created}'")
        except RedisError as error:
            logger.error(f"Fetch bot state failed with: '{error}'")
            raise StoreUnavailable
