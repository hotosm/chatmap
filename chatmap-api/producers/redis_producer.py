from redis import asyncio


class RedisProducer:
    def __init__(self, redis_client: asyncio.Redis):
        self.client = redis_client

    async def add_entry(self, stream_name: str, entry: dict, stream_id: str = "*") -> str:
        return await self.client.xadd(stream_name, entry, id=stream_id)

    async def delete_entry(self, stream_name: str, entry_id: str) -> None:
        await self.client.xdel(stream_name, entry_id)

    async def delete_all_entries(self, stream_name: str) -> None:
        await self.client.xtrim(stream_name, maxlen=0)
