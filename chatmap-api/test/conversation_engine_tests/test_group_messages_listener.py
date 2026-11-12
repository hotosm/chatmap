import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from consumers.group_messages_listener import (
    BATCH_SIZE,
    BATCHES_PER_ROUND,
    PRUNE_EVERY_SECONDS,
    GroupMessagesListener,
    prune_group_messages,
)
from results.error import StoreUnavailable
from store.received_messages_store import ReceivedMessage


def _message(message_id, is_group="1"):
    return ReceivedMessage.from_dict({
        "id": message_id, "user": "device-1", "from": "sender-1", "chat": "chat-1",
        "fromenc": "", "chatenc": "", "is_group": is_group, "text": "", "date": "2026-10-22T12:00:00",
        "location": "", "photo": "", "video": "", "audio": "", "file": "",
    })


def _listener(pending=(), new=()):
    listener = GroupMessagesListener(client=MagicMock())
    listener.store = MagicMock()
    listener.store.get_pending_messages_for = AsyncMock(return_value=list(pending))
    listener.store.get_new_messages_for = AsyncMock(side_effect=[list(batch) for batch in new] + [[]])
    listener.store.mark_message_as_processed = AsyncMock()
    return listener


def _acked(listener):
    return [call.kwargs["message_id"] for call in listener.store.mark_message_as_processed.await_args_list]


async def test_it_reads_the_streams_with_its_own_consumer_group_a_batch_at_a_time():
    listener = GroupMessagesListener(client=MagicMock())

    assert listener.store.group_name == "group-messages-store-group"
    assert listener.store.batch_size == BATCH_SIZE


async def test_only_group_messages_are_kept_and_the_whole_batch_is_marked_as_processed():
    group, private = _message("1-0"), _message("2-0", is_group="0")
    listener = _listener(new=[[group, private]])

    with patch("consumers.group_messages_listener.GroupMessagesStore.save", AsyncMock()) as save:
        await listener.process_messages_of("device-1", asyncio.Semaphore(1))

    save.assert_awaited_once_with("device-1", [group])
    assert _acked(listener) == [["1-0", "2-0"]]


async def test_it_keeps_reading_while_batches_are_full():
    full = [_message(f"{i}-0") for i in range(BATCH_SIZE)]
    listener = _listener(new=[full, [_message("last-0")]])

    with patch("consumers.group_messages_listener.GroupMessagesStore.save", AsyncMock()):
        await listener.process_messages_of("device-1", asyncio.Semaphore(1))

    assert listener.store.get_new_messages_for.await_count == 2
    assert _acked(listener)[-1] == ["last-0"]


async def test_a_batch_that_could_not_be_kept_is_read_again():
    listener = _listener(new=[[_message("1-0")]])

    with patch("consumers.group_messages_listener.GroupMessagesStore.save", AsyncMock(side_effect=StoreUnavailable)):
        await listener.process_messages_of("device-1", asyncio.Semaphore(1))

    assert _acked(listener) == []


async def test_a_device_with_a_backlog_gets_a_few_batches_per_round_and_lets_the_others_go():
    full = [_message(f"{i}-0") for i in range(BATCH_SIZE)]
    listener = _listener(new=[full] * (BATCHES_PER_ROUND + 3))

    with patch("consumers.group_messages_listener.GroupMessagesStore.save", AsyncMock()):
        await listener.process_messages_of("device-1", asyncio.Semaphore(1))

    assert listener.store.get_new_messages_for.await_count == BATCHES_PER_ROUND


async def test_one_device_failing_does_not_stop_the_others():
    listener = _listener(new=[[_message("1-0")]])

    with patch("consumers.group_messages_listener.GroupMessagesStore.save", AsyncMock(side_effect=RuntimeError)):
        await listener.process_messages_of("device-1", asyncio.Semaphore(1))


async def test_old_messages_are_removed_every_hour_even_when_removing_them_fails():
    prune = AsyncMock(side_effect=[StoreUnavailable(), 3])
    # Stops after the second round
    sleep = AsyncMock(side_effect=[None, asyncio.CancelledError()])

    with patch("consumers.group_messages_listener.GroupMessagesStore.prune", prune), \
            patch("consumers.group_messages_listener.asyncio.sleep", sleep), \
            pytest.raises(asyncio.CancelledError):
        await prune_group_messages()

    assert prune.await_count == 2
    sleep.assert_awaited_with(PRUNE_EVERY_SECONDS)
