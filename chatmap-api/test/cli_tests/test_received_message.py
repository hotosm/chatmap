from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from cli.cli import app
from store.received_messages_store import ReceivedMessage

runner = CliRunner()


def _invoke(*args):
    client = AsyncMock()
    with patch("cli.cli._build_client", return_value=client):
        result = runner.invoke(app, ["received-message", *args])
    entries = [call.args[1] for call in client.xadd.await_args_list]
    return result, entries


def test_send_writes_a_private_chat_entry_by_default():
    result, entries = _invoke("send", "--device", "demo", "--kind", "text", "--text", "hi", "--peer", "alice")

    assert result.exit_code == 0
    assert entries[0]["from"] == "alice"
    assert entries[0]["chat"] == "alice"
    assert entries[0]["is_group"] == "0"


def test_send_group_writes_the_group_as_chat_and_the_sender_as_from():
    result, entries = _invoke(
        "send", "--device", "demo", "--kind", "text", "--text", "hi",
        "--group", "--chat", "group-north", "--sender", "alice",
    )

    assert result.exit_code == 0
    assert entries[0]["from"] == "alice"
    assert entries[0]["chat"] == "group-north"
    assert entries[0]["is_group"] == "1"


def test_send_group_uses_default_chat_and_peer_as_sender():
    result, entries = _invoke("send", "--device", "demo", "--kind", "text", "--text", "hi", "--group", "--peer", "bob")

    assert result.exit_code == 0
    assert entries[0]["from"] == "bob"
    assert entries[0]["chat"] == "sim-group"


def test_add_writes_private_chat_entries_by_default():
    result, entries = _invoke("add", "--device", "demo", "--entry-type", "text", "--count", "3")

    assert result.exit_code == 0
    assert [entry["chat"] for entry in entries] == ["chat-0", "chat-1", "chat-2"]
    assert {entry["is_group"] for entry in entries} == {"0"}


def test_add_writes_dates_without_microseconds():
    _, entries = _invoke("add", "--device", "demo", "--entry-type", "text", "--count", "1")

    assert "." not in entries[0]["date"]


def test_add_group_shares_one_chat_between_distinct_senders():
    result, entries = _invoke("add", "--device", "demo", "--entry-type", "text", "--count", "3", "--group")

    assert result.exit_code == 0
    assert {entry["chat"] for entry in entries} == {"chat-group-0"}
    assert len({entry["from"] for entry in entries}) == 3
    assert {entry["is_group"] for entry in entries} == {"1"}


def test_add_groups_spreads_entries_across_groups():
    result, entries = _invoke(
        "add", "--device", "demo", "--entry-type", "text", "--count", "6", "--group", "--groups", "3",
    )

    assert result.exit_code == 0
    assert [entry["chat"] for entry in entries] == [
        "chat-group-0", "chat-group-1", "chat-group-2",
        "chat-group-0", "chat-group-1", "chat-group-2",
    ]


def test_add_groups_needs_group():
    result, entries = _invoke("add", "--device", "demo", "--entry-type", "text", "--groups", "3")

    assert result.exit_code != 0
    assert entries == []


def test_send_entries_are_parsed_by_the_received_messages_store():
    _, private_entries = _invoke("send", "--device", "demo", "--kind", "text", "--text", "hi")
    _, group_entries = _invoke("send", "--device", "demo", "--kind", "text", "--text", "hi", "--group")

    assert ReceivedMessage.from_dict(private_entries[0]).is_private_chat()
    assert not ReceivedMessage.from_dict(group_entries[0]).is_private_chat()


def test_add_entries_are_parsed_by_the_received_messages_store():
    _, private_entries = _invoke("add", "--device", "demo", "--entry-type", "text", "--count", "1")
    _, group_entries = _invoke("add", "--device", "demo", "--entry-type", "text", "--count", "1", "--group")

    assert ReceivedMessage.from_dict(private_entries[0]).is_private_chat()
    assert not ReceivedMessage.from_dict(group_entries[0]).is_private_chat()
