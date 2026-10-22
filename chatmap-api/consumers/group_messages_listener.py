import asyncio
import logging

from redis import asyncio as async_redis

from conversation_engine.device import Devices
from db import session_scope
from results.error import StoreUnavailable
from store.group_messages_store import GroupMessagesStore
from store.received_messages_store import ReceivedMessagesStore

logger = logging.getLogger(__name__)

# How many messages of a device are read and kept at once
BATCH_SIZE = 100
# How many batches a device gets per round, so one with a backlog does not hold up the others
BATCHES_PER_ROUND = 5
# How many devices are processed at the same time
DEVICES_AT_ONCE = 10
# How often the messages kept for longer than their map says are removed
PRUNE_EVERY_SECONDS = 60 * 60


class GroupMessagesListener:
    """
    Keeps the messages of the chat groups each live map listens to, whether
    its bot is on or not. It reads the streams with its own consumer group,
    so the bot still gets every message.
    """

    def __init__(self, client: async_redis.client.Redis):
        self.store = ReceivedMessagesStore(
            client=client,
            group_name="group-messages-store-group",
            consumer_name="group-messages-store-consumer",
            batch_size=BATCH_SIZE,
        )
        self.client = client

    async def _keep(self, device: str, messages: list) -> None:
        if not messages:
            return
        await GroupMessagesStore.save(device, [message for message in messages if not message.is_private_chat()])
        await self.store.mark_message_as_processed(message_id=[message.id for message in messages], device=device)

    async def process_messages_of(self, device: str, semaphore: asyncio.Semaphore) -> None:
        # Unlike the bot, pending messages are never dropped: a batch that could not be kept
        # because the database did not answer is read again until it is (a message that
        # cannot be read is skipped on its own, see GroupMessagesStore.save)
        async with semaphore:
            try:
                # Reading creates its consumer group on the stream when it is not there yet
                await self._keep(device, await self.store.get_pending_messages_for(device))
                # Batch after batch, until the device has no new messages or used its turn
                for _ in range(BATCHES_PER_ROUND):
                    messages = await self.store.get_new_messages_for(device)
                    await self._keep(device, messages)
                    if len(messages) < BATCH_SIZE:
                        break
            except StoreUnavailable:
                # Not marked as processed: they are read again on the next round
                logger.warning(f"Group messages of device '{device}' could not be kept; they will be retried")
            except Exception:
                # One device failing does not stop the others
                logger.exception(f"Keeping group messages of device '{device}' failed")

    async def _devices(self) -> list[str]:
        """The devices with messages whose owner has a live map."""
        with session_scope() as db:
            live = await Devices.devices_with_live_map(db_session=db)
        return [device for device in await Devices.get_active_devices(redis_client=self.client) if device in live]

    async def start(self):
        semaphore = asyncio.Semaphore(DEVICES_AT_ONCE)
        # Whatever happens, the listener keeps going
        while True:
            try:
                async with asyncio.TaskGroup() as task_group:
                    for device in await self._devices():
                        task_group.create_task(self.process_messages_of(device, semaphore))
            except* StoreUnavailable:
                logger.warning("Group messages could not be read; trying again")
            except* Exception:
                logger.exception("Keeping group messages failed")
            await asyncio.sleep(2)


async def prune_group_messages() -> None:
    """
    Removes the messages kept for longer than their map says, every hour.
    It runs with the switch off too: what was kept while it was on still expires.
    """
    while True:
        try:
            removed = await GroupMessagesStore.prune()
            logger.info(f"{removed} group messages older than their map keeps them removed")
        except StoreUnavailable:
            logger.warning("Old group messages could not be removed; trying again later")
        except Exception:
            logger.exception("Removing old group messages failed")
        await asyncio.sleep(PRUNE_EVERY_SECONDS)
