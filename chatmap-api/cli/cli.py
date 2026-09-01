import base64
import enum
import logging
import typer
import asyncio
from datetime import datetime, timezone

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from redis import asyncio as async_redis
from sqlalchemy import delete, select

from bot.flows.first_time_mapping.flow import FirstTimeMappingFlow
from consumers.listener import ConversationsStateListener
from db import session_scope
from settings import CHATMAP_ENC_KEY
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
bot_state_app = typer.Typer(help="Inspect/clear the first_time_mapping bot state hash in Redis")

app.add_typer(received_message_app, name="received-message")
app.add_typer(message_to_send_app, name="message-to-send")
app.add_typer(survey_response_app, name="survey-response")
app.add_typer(bot_state_app, name="bot-state")

redis_host = "localhost"
redis_port = 6380


class EntryType(str, enum.Enum):
    text = "text"
    photo = "photo"
    video = "video"
    audio = "audio"
    location = "location"
    file = "file"


class SendKind(str, enum.Enum):
    text = "text"
    photo = "photo"
    video = "video"
    audio = "audio"
    location = "location"


def _build_client() -> async_redis.client.Redis:
    return async_redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)


def _encrypt_text(plaintext: str) -> str:
    """
    Mirror of conversation_engine.tool._decrypt_text: AES-GCM with CHATMAP_ENC_KEY,
    base64(nonce + ciphertext + tag). The bot decrypts every inbound `text` field,
    so a hand-injected message has to arrive encrypted the same way a real one does.
    """
    if not plaintext:
        return plaintext

    key = CHATMAP_ENC_KEY.encode("utf-8")
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    return base64.b64encode(nonce + ciphertext + tag).decode("utf-8")


def _bot_state_key(peer: str) -> str:
    # BotTool builds this as f"bot_state:{flow.name}:{message.sender}{message.chat}";
    # a simulated private chat uses the same value for sender (from) and chat.
    return f"bot_state:{FirstTimeMappingFlow.name}:{peer}{peer}"


def _bot_consumed_key(device: str) -> str:
    return f"bot_consumed:{device}"


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


@received_message_app.command("send")
def received_message_send(
        device: str = typer.Option(..., help="Session id (map owner_id) whose stream receives the message"),
        kind: SendKind = typer.Option(..., help="Content type of the simulated message"),
        peer: str = typer.Option("sim-peer", help="The other party; fills 'from'/'chat'/'user' consistently so it reads as a private chat"),
        text: str = typer.Option(None, help="Message body (kind=text); encrypted before it hits the stream"),
        coords: str = typer.Option(None, help="'lat,lng' (kind=location), e.g. '-34.6037,-58.3816'"),
):
    """
    Add ONE conversation-valid entry to messages:<device>, shaped like what
    chatmap-im-connector writes: stable identity, encrypted text, real
    coordinates. Use this to hand-drive the bot flow; `add` is for dummy load.
    """
    if kind == SendKind.text and not text:
        raise typer.BadParameter("kind=text needs --text")
    if kind == SendKind.location and not coords:
        raise typer.BadParameter("kind=location needs --coords 'lat,lng'")

    async def run():
        client = _build_client()
        date = datetime.now(timezone.utc).replace(microsecond=0)
        stream_id = f"{int(date.timestamp() * 1000)}-0"

        entry = {
            "id": stream_id,
            "user": device,
            "from": peer,
            "chat": peer,
            "fromenc": _encrypt_text(peer),
            "chatenc": _encrypt_text(peer),
            "text": _encrypt_text(text) if kind == SendKind.text else "",
            "date": date.isoformat(),
            "location": coords if kind == SendKind.location else "",
            "photo": f"sim photo {stream_id}" if kind == SendKind.photo else "",
            "video": f"sim video {stream_id}" if kind == SendKind.video else "",
            "audio": f"sim audio {stream_id}" if kind == SendKind.audio else "",
            "file": {
                SendKind.photo: f"{stream_id}.jpg",
                SendKind.video: f"{stream_id}.mp4",
                SendKind.audio: f"{stream_id}.opus",
            }.get(kind, ""),
        }

        entry_id = await client.xadd(_received_message_stream(device), entry, id=stream_id)
        typer.echo(f"sent {kind.value} entry {entry_id} to device '{device}' (peer '{peer}')")
        if kind == SendKind.location:
            typer.echo(f"  point_id for the survey will be: {entry_id}")
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
    with session_scope() as db:
        query = select(SurveyResponse)
        if point_id:
            query = query.filter_by(point_id=point_id)
        for row in db.execute(query).scalars():
            typer.echo({"point_id": row.point_id, "answers": row.answers})


@survey_response_app.command("delete")
def survey_response_delete(
        point_id: str = typer.Option(None, help="Only delete the row for this point id; omit to delete all rows"),
):
    """Delete rows from the survey_responses table."""
    with session_scope() as db:
        query = delete(SurveyResponse)
        if point_id:
            query = query.filter_by(point_id=point_id)
        result = db.execute(query)
        db.commit()
        typer.echo(f"deleted {result.rowcount} row(s) from survey_responses")


@bot_state_app.command("show")
def bot_state_show(peer: str = typer.Option("sim-peer", help="Peer used when sending; the state key is derived from it")):
    """Print the first_time_mapping bot state hash (state, fallback_count, point_id)."""

    async def run():
        client = _build_client()
        key = _bot_state_key(peer)
        state = await client.hgetall(key)
        typer.echo({"key": key, **state} if state else f"no bot state at '{key}'")
        await client.aclose()

    asyncio.run(run())


@bot_state_app.command("delete")
def bot_state_delete(peer: str = typer.Option("sim-peer", help="Peer used when sending; the state key is derived from it")):
    """Delete the first_time_mapping bot state hash for this peer."""

    async def run():
        client = _build_client()
        key = _bot_state_key(peer)
        removed = await client.delete(key)
        typer.echo(f"deleted '{key}'" if removed else f"no bot state at '{key}'")
        await client.aclose()

    asyncio.run(run())


@app.command("conversation-reset")
def conversation_reset(
        device: str = typer.Option(..., help="Session id (map owner_id) to clean up"),
        peer: str = typer.Option("sim-peer", help="Peer whose bot state should be cleared"),
):
    """Wipe the Redis-side state for one simulated conversation so it can be re-run."""

    async def run():
        client = _build_client()
        await client.xtrim(_received_message_stream(device), maxlen=0)
        await client.delete(_message_to_send_stream(device))
        await client.delete(_bot_consumed_key(device))
        await client.delete(_bot_state_key(peer))
        typer.echo(f"reset messages/to_send/bot_consumed for '{device}' and bot state for peer '{peer}'")
        typer.echo("note: survey_responses rows are keyed by point id; use `survey-response delete` if needed")
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
