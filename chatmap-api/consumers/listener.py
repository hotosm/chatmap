import asyncio
import logging
from datetime import datetime, timedelta

from conversation_engine.flow import Flows
from store.conversation_store import ConversationStore
from redis import asyncio as async_redis

# Logs
logger = logging.getLogger(__name__)

from asyncio import Semaphore

from consumers.redis_consumer import RedisConsumer
from conversation_engine.device import Devices
from conversation_engine.event import Event, EventName
from conversation_engine.conversation import Conversation, ConversationKey


class ConversationsStateListener:
    def __init__(self, client: async_redis.client.Redis):
        self.client = client

    async def conversations_states_for(self, device: str, semaphore: Semaphore):
        consumer = RedisConsumer(
            redis_client=self.client,
            stream_key="messages",
            group_name="cli-group",
            consumer_name="cli-consumer",
        )

        await consumer.create_group(device)
        messages = await consumer.get_messages_for(device)

        if not messages:
            logger.info("no messages to process")
        else:
            conversation_store = ConversationStore(client=self.client)

            for message in messages:
                event = Event.from_message(message)
                if event:
                    conversation_key = ConversationKey(sender=message.sender, chat=message.chat)

                    await Flows.call_tools_for(event, message, device)
                    await conversation_store.add_event(key=conversation_key, event=event)

                    conversation = await conversation_store.load(
                        key=conversation_key,
                        target_time=event.occurred_at,
                        window_time=timedelta(minutes=2)
                    )

                    await Flows.call_tools_in_end_flow(conversation)

    async def start(self):
        # TODO: semaphore should be a configurable environment variable
        semaphore = asyncio.Semaphore(4)

        while True:
            devices = await Devices.get_active_devices(self.client)

            async with asyncio.TaskGroup() as task_group:
                for device in devices:
                    task_group.create_task(self.conversations_states_for(device, semaphore))
            await asyncio.sleep(2)
