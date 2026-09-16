import asyncio
import logging
from datetime import timedelta

from conversation_engine.flow import Flows
from db import session_scope
from results.error import UnknownConversation, StoreUnavailable, BotStateWithoutPointId, BotStateWithoutQuestion, \
    BotMessagesNotConfigured
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

            except StoreUnavailable:
                logger.warning(f"The request failed due to connectivity issues; it will automatically retry")
            except UnknownConversation:
                logger.warning(f"Conversation not found; it will automatically retry")
            except BotStateWithoutPointId as error:
                logger.warning(f"Message: '{error.message_id}' with incorrect state removing from PEL")
                await flows.received_messages_store.mark_message_as_processed(
                    message_id=error.message_id,
                    device=device
                )
            except BotStateWithoutQuestion as error:
                logger.warning(f"Message: '{error.message_id}' with incorrect state removing from PEL")
                await flows.received_messages_store.mark_message_as_processed(
                    message_id=error.message_id,
                    device=device
                )
            except BotMessagesNotConfigured as error:
                await flows.received_messages_store.mark_message_as_processed(
                    message_id=error.message_id,
                    device=device
                )

    async def start(self):
        semaphore = asyncio.Semaphore(10)
        flows = Flows(client=self.client)

        logger.debug("Conversations flows is setup!")

        while True:
            with session_scope() as db:
                devices = await Devices.devices_to_process(
                    redis_client=self.client,
                    db_session=db
                )

            try:
                async with asyncio.TaskGroup() as task_group:
                    for device in devices:
                        task_group.create_task(
                            self.process_conversation_for(device=device, flows=flows, semaphore=semaphore)
                        )
            except* Exception as eg:
                logger.exception("Process failed for one or more devices: %s", eg.exceptions)
            await asyncio.sleep(2)
