import logging

from redis import asyncio as async_redis
from abc import ABC, abstractmethod
from producers.redis_producer import RedisProducer

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Async, non-blocking side effect bound to a (Flow, State) pair.

    The engine never consumes a return value and never lets a Tool's failure
    propagate past the dispatch site — implementations don't need to guard
    against that themselves.
    """

    # TODO: dont use __call__
    @abstractmethod
    async def __call__(
            self,
            data: dict,
    ) -> None:
        ...


class LogTool(Tool):
    """v1 stub Tool binding: logs instead of doing real work."""

    async def __call__(
            self,
            data: dict
    ) -> None:
        logger.info(f"{data["log_message"]} %s", data["log_arg"])


class BotTool(Tool):
    async def __call__(
            self,
            data: dict
    ) -> None:
        # TODO: pass client as parameter
        redis_host = "localhost"
        redis_port = 6380
        client = async_redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

        producer = RedisProducer(client=client, stream_key="to_send")
        entry = {
            "to": data["to"],
            "text": data["message"],
        }
        await producer.add_entry_for(device=data["device"], entry=entry)
