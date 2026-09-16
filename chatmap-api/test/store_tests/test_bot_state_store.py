from enum import Enum, auto
from unittest.mock import AsyncMock

from store.bot_state_store import BotStateStore


class _State(Enum):
    IDLE = auto()
    WAITING = auto()


def _make_store():
    client = AsyncMock()
    return BotStateStore(client), client


async def test_save_state_resets_fallback_count_by_default():
    store, client = _make_store()

    await store.save_state(bot_state_key="key-1", state=_State.WAITING)

    client.hset.assert_awaited_once_with("key-1", mapping={"state": "WAITING", "fallback_count": "0"})


async def test_save_state_can_skip_the_fallback_count_reset():
    store, client = _make_store()

    await store.save_state(bot_state_key="key-1", state=_State.WAITING, reset_fallback_count=False)

    client.hset.assert_awaited_once_with("key-1", mapping={"state": "WAITING"})


async def test_save_state_lets_bot_info_override_the_default_reset():
    store, client = _make_store()

    await store.save_state(
        bot_state_key="key-1", state=_State.WAITING, bot_info={"fallback_count": "4"}
    )

    client.hset.assert_awaited_once_with("key-1", mapping={"state": "WAITING", "fallback_count": "4"})


async def test_save_state_merges_bot_info_alongside_the_reset():
    store, client = _make_store()

    await store.save_state(
        bot_state_key="key-1", state=_State.WAITING, bot_info={"point_id": "p-1"}
    )

    client.hset.assert_awaited_once_with(
        "key-1", mapping={"state": "WAITING", "fallback_count": "0", "point_id": "p-1"}
    )
