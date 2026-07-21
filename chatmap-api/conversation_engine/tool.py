import logging

from redis import asyncio as async_redis
from events.message_event import MessageEvent
from conversation_engine.event import Event
from producers.redis_producer import RedisProducer

logger = logging.getLogger(__name__)


class LogTool:
    """v1 stub Tool binding: logs instead of doing real work."""

    async def __call__(
            self,
            data: dict
    ) -> None:
        logger.info(f"{data["log_message"]} %s", data["log_arg"])


class BotTool:
    def __init__(self):
        redis_host = "localhost"
        redis_port = 6380
        self.client = async_redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

    async def __call__(self, event: Event, message: MessageEvent, device: str):
        producer = RedisProducer(client=self.client, stream_key="to_send")
        entry = {
            "to": message.sender,
            "text": f"{event.name}!",
        }
        await producer.add_entry_for(device=device, entry=entry)
