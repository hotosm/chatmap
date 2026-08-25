import enum
import logging
import typer
import asyncio
from datetime import datetime, timezone
from redis import asyncio as async_redis
from sqlalchemy import delete, select

from consumers.listener import ConversationsStateListener
from db import get_db_session
from store.message_to_send_store import MessageToSendStore
from store.survey_responses_store import SurveyResponse

logging.basicConfig(
    format='[CLI] %(levelname)s: %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = typer.Typer()
received_message_app = typer.Typer(help="Manage entries on the messages stream (inbound webhook events)")
message_to_send_app = typer.Typer(help="Manage entries on the to_send stream (chatmap-im-connector delivery queue)")
survey_response_app = typer.Typer(help="Inspect entries in the survey_responses table")

app.add_typer(received_message_app, name="received-message")
app.add_typer(message_to_send_app, name="message-to-send")
app.add_typer(survey_response_app, name="survey-response")

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


def _received_message_stream(device: str) -> str:
    return f"messages:{device}"


def _message_to_send_stream(device: str) -> str:
    return f"to_send:{device}"


@received_message_app.command("add")
def received_message_add(
        device: str = typer.Option(..., help="Session id whose stream will receive the entries"),
        entry_type: EntryType = typer.Option(..., help="Kind of message content to simulate"),
        count: int = typer.Option(5, help="How many entries to add"),
):
    """Add `count` test entries of a given type to the received messages stream."""

    async def run():
        client = _build_client()
        for i in range(count):
            date = datetime.now(timezone.utc)
            # Sequence part uses `i` so entries within the same millisecond don't collide
            stream_id = f"{int(date.timestamp() * 1000)}-{i}"
            entry = {
                "user": f"user-{i}",
                "from": f"from-{i}",
                "chat": f"chat-{i}",
                "fromenc": f"fromenc-{i}",
                "chatenc": f"chatenc-{i}",
                "text": "",
                "date": date.isoformat(),
                "location": "",
                "photo": "",
                "video": "",
                "audio": "",
                "file": "",
                entry_type.value: f"test {entry_type.value} {i}"
            }
            entry_id = await client.xadd(_received_message_stream(device), entry, id=stream_id)
            typer.echo(f"added entry {entry_id}")

        await client.aclose()

    asyncio.run(run())


@received_message_app.command("delete")
def received_message_delete(device: str = typer.Option(..., help="Session id whose stream will be cleared")):
    """Delete every entry in the received messages stream, read or not."""

    async def run():
        client = _build_client()
        await client.xtrim(_received_message_stream(device), maxlen=0)
        typer.echo(f"deleted all entries from device '{device}'")
        await client.aclose()

    asyncio.run(run())


@received_message_app.command("list")
def received_message_list(device: str = typer.Option(..., help="Session id whose stream will be listed")):
    """List every entry currently in the received messages stream."""

    async def run():
        client = _build_client()
        entries = await client.xrange(_received_message_stream(device))
        for entry_id, fields in entries:
            typer.echo({"id": entry_id, **fields})
        await client.aclose()

    asyncio.run(run())


@message_to_send_app.command("add")
def message_to_send_add(
        device: str = typer.Option(..., help="Session id whose outbound stream will receive the message"),
        to: str = typer.Option(...,
                               help="Encrypted recipient JID, as received in the 'from' field of a messages:<device> entry"),
        message: str = typer.Option(..., help="Text of the message to send"),
):
    """Queue a text message on the to_send stream for chatmap-im-connector to deliver."""

    async def run():
        client = _build_client()
        store = MessageToSendStore(client=client)
        await store.send_message(sender=device, to=to, messages=message)
        typer.echo(f"queued message for device '{device}' -> {to}")
        await client.aclose()

    asyncio.run(run())


@message_to_send_app.command("delete")
def message_to_send_delete(device: str = typer.Option(..., help="Session id whose stream will be cleared")):
    """Delete every entry in the to_send stream."""

    async def run():
        client = _build_client()
        await client.xtrim(_message_to_send_stream(device), maxlen=0)
        typer.echo(f"deleted all entries from device '{device}'")
        await client.aclose()

    asyncio.run(run())


@message_to_send_app.command("list")
def message_to_send_list(device: str = typer.Option(..., help="Session id whose stream will be listed")):
    """List every entry currently in the to_send stream."""

    async def run():
        client = _build_client()
        entries = await client.xrange(_message_to_send_stream(device))
        for entry_id, fields in entries:
            typer.echo({"id": entry_id, **fields})
        await client.aclose()

    asyncio.run(run())


@survey_response_app.command("list")
def survey_response_list(
        point_id: str = typer.Option(None, help="Only list the row for this point id"),
):
    """List every row currently in the survey_responses table."""
    db = get_db_session()
    query = select(SurveyResponse)
    if point_id:
        stmt = query.filter_by(point_id=point_id)
    for row in db.execute(query).scalars():
        typer.echo({"point_id": row.point_id, "answers": row.answers})


@survey_response_app.command("delete")
def survey_response_delete(
        point_id: str = typer.Option(None, help="Only delete the row for this point id; omit to delete all rows"),
):
    """Delete rows from the survey_responses table."""
    db = get_db_session()
    query = delete(SurveyResponse)
    if point_id:
        query = query.filter_by(point_id=point_id)
    result = db.execute(query)
    db.commit()
    typer.echo(f"deleted {result.rowcount} row(s) from survey_responses")


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
