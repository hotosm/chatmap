"""
Keeps track of the messages the bot consumed as answers to its own questions,
so the mapping pipeline can tell them apart from the content a user meant to
put on the map.

WHY THIS EXISTS
---------------
Two pipelines read the same Redis stream and know nothing about each other:

  * `stream.py` -> `data.py` -> chatmap_py, the original mapping pipeline. It
    pairs every location with the closest message in time from the same user,
    in either direction. It has no notion of a conversation.
  * `consumers/listener.py` -> conversation_engine, the bot. It asks questions
    and the user answers them with short option codes ("1", "2", ...).

Those answers are just text sitting near a location, so the pairing happily
picks one over the photo it was supposed to describe -- the option code ends
up on the map and the photo is dropped. Marking the answers here, and
filtering them out in `stream.py`, is what keeps the two pipelines from
stepping on each other.

TRANSITIONAL
------------
This store is a seam, not a destination. We chose to keep the original mapping
pipeline running as-is rather than rework production code, and this is the
cheapest correct way to make both coexist. The direction we want is to move
mapping into the conversation engine flow, which already knows exactly which
message is a location, which is content and which is an answer -- it does not
have to guess by time proximity. Once mapping lives there, the filtering in
`stream.py` and this whole store should be deleted.
"""

import logging

from datetime import datetime
from redis import RedisError
from results.error import StoreUnavailable
from typing import Sequence

from redis.asyncio.client import Redis as RedisClient

logger = logging.getLogger(__name__)


class BotConsumedMessagesStore:
    """
    Stores consumed message ids in a sorted set per device, scored by the time
    the message was sent.

    The score is what makes this cheap to keep in sync with the stream: marks
    are trimmed by age with the very same cutoff `stream.py` already uses to
    trim the stream itself, so a mark is dropped in the same pass as the entry
    it refers to -- never before it, which would let the entry be mapped again.
    """

    def __init__(self, client: RedisClient):
        self.client = client

    @staticmethod
    def _key(device: str) -> str:
        return f"bot_consumed:{device}"

    async def mark_consumed(self, device: str, message_id: str, occurred_at: datetime) -> None:
        """
        Records that the bot consumed a message, so it is never offered to the
        mapping pipeline as content.

        Args:
            device (str): session the message belongs to, as used in the stream key.
            message_id (str): the Redis stream entry id of the message.
            occurred_at (datetime): when the message was sent; becomes the score.
        """
        score = occurred_at.timestamp() * 1000

        try:
            await self.client.zadd(self._key(device), {message_id: score})
            logger.debug(f"Message '{message_id}' marked as consumed by the bot")

        except RedisError as error:
            logger.error(f"Marking message '{message_id}' as consumed by the bot failed with: '{error}'")
            raise StoreUnavailable

    async def is_consumed(self, device: str, message_id: str) -> bool:
        """
        Whether the bot already handled this message. Handlers that mark a
        message consumed use this to no-op on redelivery instead of acting on
        a stale message again.
        """
        try:
            return await self.client.zscore(self._key(device), message_id) is not None

        except RedisError as error:
            logger.error(f"Checking if message '{message_id}' was consumed by the bot failed with: '{error}'")
            raise StoreUnavailable

    async def discard_bot_messages(self, device: str, entries: Sequence) -> list:
        """
        Given a batch of stream entries, returns only the ones the bot did not
        consume, preserving their order.

        Args:
            device (str): session the entries belong to.
            entries (Sequence): stream entries as returned by `xrange`, each a
                tuple of (entry_id, fields).

        Returns:
            list: the entries that are still candidates for mapping.
        """
        if not entries:
            return list(entries)

        try:
            scores = await self.client.zmscore(
                self._key(device), [entry_id for entry_id, _ in entries]
            )

        except RedisError as error:
            logger.error(f"Fetching messages consumed by the bot failed with: '{error}'")
            raise StoreUnavailable

        # zmscore returns None for members that are not in the sorted set,
        # so a score means "the bot consumed this one".
        return [entry for entry, score in zip(entries, scores) if score is None]

    async def cleanup(self, device: str, cutoff_time_ms: int) -> None:
        """
        Drops marks older than the cutoff. Meant to be called with the same
        cutoff used to trim the stream, so both expire together.

        Args:
            device (str): session whose marks will be cleaned up.
            cutoff_time_ms (int): epoch milliseconds; marks older than this go away.
        """
        try:
            removed = await self.client.zremrangebyscore(self._key(device), "-inf", cutoff_time_ms)
            logger.info(f"cleanup: {removed} bot consumed marks deleted")

        except RedisError as error:
            logger.error(f"Cleaning up messages consumed by the bot failed with: '{error}'")
            raise StoreUnavailable
