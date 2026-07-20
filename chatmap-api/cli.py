import enum
import logging
import typer
import asyncio
from datetime import datetime, timezone
from redis import asyncio as async_redis

from producers.redis_producer import RedisProducer
from consumers.redis_consumer import RedisConsumer
from consumers.listener import ConversationsStateListener

logging.basicConfig(
    format='[CLI] %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = typer.Typer()

redis_host = "localhost"
redis_port = 6380


class EntryType(str, enum.Enum):
    text = "text"
    photo = "photo"
    video = "video"
    audio = "audio"
    location = "location"
    file = "file"


def _build_client() -> async_redis.client.Redis:
    return async_redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)


def _stream_key() -> str:
    return "messages"


@app.command("delete-all-entries")
def delete_all_entries(device: str = typer.Option(..., help="Session id whose stream will be cleared")):
    """Delete every entry in a Redis stream, read or not."""

    async def run():
        client = _build_client()
        producer = RedisProducer(client=client, stream_key=_stream_key())
        await producer.delete_all_entries_for(device)

        typer.echo(f"deleted all entries from device '{device}'")

        await client.aclose()

    asyncio.run(run())


@app.command("add-entries")
def add_entries(
        device: str = typer.Option(..., help="Session id whose stream will receive the entries"),
        entry_type: EntryType = typer.Option(..., help="Kind of message content to simulate"),
        count: int = typer.Option(5, help="How many entries to add"),
):
    """Add `count` test entries of a given type to a Redis stream."""

    async def run():
        client = _build_client()
        producer = RedisProducer(client=client, stream_key=_stream_key())
        for i in range(count):
            date = datetime.now(timezone.utc)
            # Sequence part uses `i` so entries within the same millisecond don't collide
            stream_id = f"{int(date.timestamp() * 1000)}-{i}"
            entry = {
                "id": stream_id,
                "user": f"user-{i}",
                "from": f"from-{i}",
                "chat": f"chat-{i}",
                "text": "",
                "date": date.isoformat(),
                "location": "",
                "photo": "",
                "video": "",
                "audio": "",
                "file": "",
                entry_type.value: f"test {entry_type.value} {i}"
            }
            entry_id = await producer.add_entry_for(device=device, entry=entry, stream_id=stream_id)
            typer.echo(f"added entry {entry_id}")

        await client.aclose()

    asyncio.run(run())


@app.command("list-entries")
def list_messages(device: str = typer.Option(..., help="Session id whose stream will be listed")):
    async def run():
        client = _build_client()
        consumer = RedisConsumer(
            redis_client=client,
            stream_key=_stream_key(),
            group_name="cli-group",
            consumer_name="cli-consumer",
        )
        messages = await consumer.list_messages_for(device)
        for message in messages:
            typer.echo(message)

        await client.aclose()

    asyncio.run(run())


@app.command("conversations-listener")
def conversations_listener():
    """List every entry in a Redis stream and report which State(s), if any, it matches."""

    async def run():
        client = _build_client()
        listener = ConversationsStateListener(client=client)

        try:
            await listener.start()
        finally:
            await client.aclose()

    asyncio.run(run())


if __name__ == "__main__":
    app()
