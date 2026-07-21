import logging
import textwrap
import re

from redis import asyncio as async_redis
from data import decrypt_message
from events.message_event import MessageEvent
from conversation_engine.event import Event, EventName
from producers.redis_producer import RedisProducer

logger = logging.getLogger(__name__)


class LogTool:
    """v1 stub Tool binding: logs instead of doing real work."""

    async def __call__(
            self,
            data: dict
    ) -> None:
        logger.info(data["log_message"], data["log_arg"])


class BotTool:
    def __init__(self):
        redis_host = "localhost"
        redis_port = 6380
        self.client = async_redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

    async def __call__(self, event: Event, message: MessageEvent, device: str):
        producer = RedisProducer(client=self.client, stream_key="to_send")

        if event.name == EventName.USER_SEND_TEXT:
            _sos_regex = re.compile(r"\b(?:a[yj]uda|help)\b", re.IGNORECASE)
            # TODO: move this logic to the MessageEvent scope
            decrypted_message = decrypt_message(message.text)
            ask_for_help = _sos_regex.search(decrypted_message)

            if ask_for_help:
                entry = {
                    "to": message.sender,
                    "text": textwrap.dedent("""\
                            ¡Hola! 👋 Soy el bot de ChatMap.
    
                            Para mapear tu contenido hacé esto:
    
                            1️⃣ Mandame una *foto*, un *video* o un *audio*.
                            2️⃣ Después, en un *mensaje aparte*, compartime la *ubicación* donde querés que quede mapeado.
    
                            📍 Para compartir la ubicación: 
                            1️⃣ tocá el clip (📎)
                            2️⃣ elegí *Ubicación*.
    
                            ¡Listo! Con esos dos pasos tu archivo queda en el mapa. 🗺️"""),
                }
            else:
                entry = {
                    "to": message.sender,
                    "text": f"{event.name}!",
                }
        else:
            entry = {
                "to": message.sender,
                "text": f"{event.name}!",
            }

        await producer.add_entry_for(device=device, entry=entry)
