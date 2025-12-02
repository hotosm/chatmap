import redis.asyncio as redis
import time
import os
import logging
import asyncio
from data import process_chat_entries
from settings import STREAM_KEY, EXPIRING_MIN_MS, STREAM_LISTENER_TIME

# Logs
logger = logging.getLogger(__name__)

# Redis config
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)

# Cleanup old messages
async def cleanup(user: str):
    cutoff_time_ms = int(time.time() * 1000) - EXPIRING_MIN_MS
    cutoff_id = f"{cutoff_time_ms}-0"
    entries = await redis_client.xrange(f"{STREAM_KEY}:{user}", min='-', max=cutoff_id)
    # Remove data older than (EXPIRING_MIN_MS) minutes
    for entry_id, _ in entries:
        await redis_client.xdel(f"{STREAM_KEY}:{user}", entry_id)
    logger.info(f'cleanup: {len(entries)} messages deleted')

# Get all sessions
async def get_sessions():
    sessions = await redis_client.scan(0, match="messages:*", type="stream")
    return [item[0].decode('utf-8').replace("messages:", "") for item in sessions if item]

# This function runs every (STREAM_LISTENER_TIME) seconds.
# It gets a list of user sessions and then messages
# from the Redis queue for processing them with ChatMap by
# calling process_chat_entries , which will also update
# the database and download media files
# It also cleanup old messages from the queue.
async def stream_listener() -> None:
    while True:
        try:
            sessions = await get_sessions()
            for user in sessions:
                entries = await redis_client.xrange(f'{STREAM_KEY}:{user}', min='-', max='+')
                logger.info(f"{len(entries)} entries for user {user}")
                await process_chat_entries(user, entries)
                # Cleanup old messages
                await cleanup(user)
        except Exception as e:
            logger.info("[stream_listener] Error processing data %s", e)
        await asyncio.sleep(STREAM_LISTENER_TIME)
