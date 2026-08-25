import logging

from redis import asyncio as async_redis
from sqlalchemy.orm import Session
from db import Map
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from redis import RedisError

from results.error import StoreUnavailable

# Logs
logger = logging.getLogger(__name__)


class Devices:
    @classmethod
    async def get_active_devices(cls, redis_client: async_redis.client.Redis) -> list[str]:
        devices = []

        try:
            # TODO: remove hardcoded stream name "messages"
            async for entry in redis_client.scan_iter(match="messages:*", type="stream"):
                entry_without_stream_name = entry.replace("messages:", "")
                devices.append(entry_without_stream_name)

            return devices
        except RedisError:
            logger.warning("Could not read active devices")
            raise StoreUnavailable

    @classmethod
    async def devices_with_active_bot(cls, db_session: Session) -> set[str]:
        try:
            query = select(Map.owner_id).where(Map.is_live, Map.bot_active)
            return set(db_session.execute(query).scalars())
        except SQLAlchemyError as error:
            logger.error(f"Fetch devices with active bot failed with: '{error}'")
            raise StoreUnavailable

    @classmethod
    async def devices_to_process(cls, redis_client: async_redis.client.Redis, db_session: Session) -> list[str]:
        active_devices = await cls.get_active_devices(redis_client=redis_client)
        devices_with_active_bot = await cls.devices_with_active_bot(db_session=db_session)

        return [active_device for active_device in active_devices if active_device in devices_with_active_bot]
