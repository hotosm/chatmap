import asyncio
import logging
from datetime import timedelta

from conversation_engine.flow import Flows
from results.error import UnknownConversation, StoreUnavailable
from store.conversation_store import ConversationStore
from redis import asyncio as async_redis

from store.received_messages_store import ReceivedMessage

# Logs
logger = logging.getLogger(__name__)

from asyncio import Semaphore
from conversation_engine.device import Devices
from conversation_engine.event import Event
from conversation_engine.conversation import ConversationKey


class ConversationsStateListener:
    def __init__(self, client: async_redis.client.Redis):
        self.client = client

    async def _process(self, message: ReceivedMessage, device: str, flows: Flows) -> None:
        if message.is_private_chat():
            conversation_store = ConversationStore(client=self.client)
            event = Event.from_message(message)

            if event:
                conversation_key = ConversationKey(sender=message.sender, chat=message.chat)

                await conversation_store.add_event(key=conversation_key, event=event)

                conversation = await conversation_store.load(
                    key=conversation_key,
                    target_time=event.occurred_at,
                    window_time=timedelta(minutes=2)
                )

                logger.info(f"Event: '{event.name}' received calling tools...")

                await flows.call_tools_for(
                    event=event,
                    message=message,
                    device=device,
                    conversation=conversation
                )
            else:
                logger.warning("Unknown event for message: %s", message)
        else:
            logger.warning("Currently we are not processing messages from groups")

    async def process_conversation_for(self, device: str, flows: Flows, semaphore: Semaphore):
        async with semaphore:
            try:
                await flows.received_messages_store.setup_store_for(device=device)
                await flows.received_messages_store.prune_pending_messages_for(device=device)

                messages: list[ReceivedMessage] = await flows.received_messages_store.get_pending_messages_for(device)
                messages.extend(await flows.received_messages_store.get_new_messages_for(device))

                if messages:
                    for message in messages:
                        logger.debug("A message arrives!")
                        await self._process(message=message, device=device, flows=flows)
                        await flows.received_messages_store.mark_message_as_processed(message_id=message.id,
                                                                                      device=device)

                logger.info("no messages to process")
            except StoreUnavailable:
                logger.warning(f"The request failed due to connectivity issues; it will automatically retry")
            except UnknownConversation:
                logger.warning(f"Conversation not found; it will automatically retry")

    async def start(self):
        semaphore = asyncio.Semaphore(10)
        flows = Flows(client=self.client)

        logger.debug("Conversations flows is setup!")

        while True:
            devices = await Devices.get_active_devices(self.client)

            async with asyncio.TaskGroup() as task_group:
                for device in devices:
                    task_group.create_task(
                        self.process_conversation_for(device=device, flows=flows, semaphore=semaphore)
                    )
            await asyncio.sleep(2)
