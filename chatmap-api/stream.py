"""
This module implements a Redis stream listener that ingests real-time instant messages 
from Redis streams and processes them to generate maps. It continuously monitors active 
user sessions, retrieves new message entries from their respective Redis streams, 
and passes them to the processing function for map creation and data updates. 

The module also includes automatic cleanup of old messages from streams based on a 
configured expiration time.
"""


import redis.asyncio as redis
import time
import os
import logging
import asyncio
from data import process_chat_entries
from settings import STREAM_KEY, EXPIRING_MIN_MS, STREAM_LISTENER_TIME, DISABLE_STREAM_CLEANUP

# Logs
logger = logging.getLogger(__name__)

# Redis connection configuration
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)

# Cleanup old messages
async def cleanup(user: str):
    """
    Removes old entries from a Redis stream for a given user.
    
    The function calculates a cutoff time based on the current time minus the 
    expiration threshold (EXPIRING_MIN_MS). It then deletes all entries in the 
    stream that are older than this cutoff.

    Args:
        user (str): The identifier of the user whose stream will be cleaned up.
    """
    cutoff_time_ms = int(time.time() * 1000) - EXPIRING_MIN_MS
    cutoff_id = f"{cutoff_time_ms}-0"
    entries = await redis_client.xrange(f"{STREAM_KEY}:{user}", min='-', max=cutoff_id)
    # Remove data older than (EXPIRING_MIN_MS) minutes
    for entry_id, _ in entries:
        await redis_client.xdel(f"{STREAM_KEY}:{user}", entry_id)
    logger.info(f'cleanup: {len(entries)} messages deleted')

# Get all sessions
async def get_sessions():
    """
    Retrieves all active user sessions from Redis by scanning for keys matching 
    the pattern 'messages:*' which represent streams for individual users.

    Returns:
        list: A list of user identifiers (strings) corresponding to active sessions.
    """
    keys = []
    async for key in redis_client.scan_iter(match="messages:*", type="stream"):
        keys.append(key.decode("utf-8").replace("messages:", ""))
    return keys

async def stream_listener() -> None:
    """
    Main asynchronous listener loop that periodically processes Redis streams 
    for all active user sessions. For each session, it retrieves new messages 
    from the stream and passes them to `process_chat_entries` for further handling.

    Additionally, this function cleans up old messages from each stream if 
    cleanup is not disabled via the DISABLE_STREAM_CLEANUP setting.

    This function runs continuously, sleeping between iterations as defined by 
    STREAM_LISTENER_TIME (in seconds).

    Side Effects:
        - Processes chat entries using `process_chat_entries`.
        - May delete old entries from Redis streams depending on cleanup settings.
    """
    while True:
        try:
            sessions = await get_sessions()
            for user in sessions:
                entries = await redis_client.xrange(f'{STREAM_KEY}:{user}', min='-', max='+')
                logger.info(f"{len(entries)} entries for user {user}")
                await process_chat_entries(user, entries)
                # Cleanup old messages
                if not DISABLE_STREAM_CLEANUP:
                    await cleanup(user)
        except Exception as e:
            logger.info("[stream_listener] Error processing data %s", e)
        await asyncio.sleep(STREAM_LISTENER_TIME)
