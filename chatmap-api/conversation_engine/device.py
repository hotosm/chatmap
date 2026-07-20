from redis import asyncio as async_redis


class Devices:
    @classmethod
    async def get_active_devices(cls, client: async_redis.client.Redis) -> list[str]:
        devices = []

        # TODO: remove hardcoded stream name "messages"
        async for entry in client.scan_iter(match="messages:*", type="stream"):
            entry_without_stream_name = entry.replace("messages:", "")
            devices.append(entry_without_stream_name)

        return devices
