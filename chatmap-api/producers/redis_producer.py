from redis import asyncio


class RedisProducer:
    def __init__(self, client: asyncio.Redis, stream_key: str):
        self.client = client
        self.stream_key = stream_key

    def stream_name(self, device) -> str:
        return f"{self.stream_key}:{device}"

    async def add_entry_for(self, device: str, entry: dict, stream_id: str = "*") -> str:
        return await self.client.xadd(self.stream_name(device=device), entry, id=stream_id)

    async def delete_entry_for(self, device: str, entry_id: str) -> None:
        await self.client.xdel(self.stream_name(device=device), entry_id)

    async def delete_all_entries_for(self, device: str) -> None:
        await self.client.xtrim(self.stream_name(device=device), maxlen=0)
