import logging

from enum import Enum
from redis import RedisError
from results.error import StoreUnavailable

from redis.asyncio.client import Redis as RedisClient

logger = logging.getLogger(__name__)


class BotStateStore:
    def __init__(self, client: RedisClient):
        self.client = client

    async def fetch_fallback_count(self, bot_state_key: str) -> int:
        raw_count = await self.fetch_field(bot_state_key=bot_state_key, field="fallback_count")
        return int(raw_count) if raw_count else 0

    async def increment_fallback_count(self, bot_state_key: str) -> int:
        try:
            return await self.client.hincrby(bot_state_key, "fallback_count", 1)

        except RedisError as error:
            logger.error(f"Trying to increment the bot state fallback count on redis failed with: '{error}'")
            raise StoreUnavailable

    async def fetch_state(self, bot_state_key: str) -> dict:
        try:
            result = await self.client.hgetall(bot_state_key)
            return result


        except RedisError as error:
            logger.error(f"Fetch bot state failed with: '{error}'")
            raise StoreUnavailable

    async def fetch_field(self, bot_state_key: str, field: str) -> str | None:
        try:
            return await self.client.hget(bot_state_key, field)

        except RedisError as error:
            logger.error(f"Fetch bot state field failed with: '{error}'")
            raise StoreUnavailable

    async def save_state(
            self,
            bot_state_key: str,
            state: Enum,
            bot_info: dict | None = None
    ) -> None:
        fields = {"state": state.name}

        if bot_info:
            fields.update(bot_info)

        try:
            await self.client.hset(bot_state_key, mapping=fields)
            return None

        except RedisError as error:
            logger.error(f"Trying to save a bot state on redis failed with: '{error}'")
            raise StoreUnavailable

    async def delete_state(
            self,
            bot_state_key: str,
    ) -> None:
        try:
            await self.client.delete(bot_state_key)

        except RedisError as error:
            logger.error(f"Trying to delete bot state on redis failed with: '{error}'")
            raise StoreUnavailable
