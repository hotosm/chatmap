from unittest.mock import AsyncMock, MagicMock

from store.received_messages_store import ReceivedMessagesStore

FIELDS = {
    "user": "device-1", "from": "sender-1", "chat": "chat-1", "fromenc": "", "chatenc": "", "is_group": "1",
    "text": "", "date": "2026-10-22T12:00:00", "location": "", "photo": "", "video": "", "audio": "", "file": "",
}


def _store(entries):
    client = MagicMock()
    client.xgroup_create = AsyncMock(return_value=True)
    client.xreadgroup = AsyncMock(return_value=[("messages:device-1", entries)])
    client.xack = AsyncMock()
    return ReceivedMessagesStore(client=client)


async def test_a_message_that_lacks_fields_is_acked_without_holding_back_the_others():
    store = _store([("1-0", {"text": "only a text"}), ("2-0", FIELDS)])

    messages = await store.get_pending_messages_for("device-1")

    assert [message.id for message in messages] == ["2-0"]
    store.client.xack.assert_awaited_once_with("messages:device-1", "received-messages-store-group", "1-0")
