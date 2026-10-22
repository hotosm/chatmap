from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.v2.routes.messages import read_groups, read_messages, update_group
from api.v2.schemas.messages import ChatGroupChange, KeptDays
from results.error import MapNotFound


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.messages.GroupMessagesStore.{method}", AsyncMock(**kwargs))


def _patch_phone(groups):
    return patch("api.v2.routes.messages._phone_groups", AsyncMock(return_value=groups))


async def test_read_groups_asks_the_connector_for_the_groups_of_the_phone_of_the_user():
    phone = [{"chat": "hash-1", "name": "North"}]
    group = SimpleNamespace(chat="c-1", name="North", enabled=True)

    with _patch_phone(phone) as phone_groups, _patch_store("groups", return_value=([group], 30)) as store:
        result = await read_groups(map_id="map-1", user=_user())

    phone_groups.assert_awaited_once_with("user-1")
    store.assert_awaited_once_with("map-1", "user-1", phone)
    assert [(item.id, item.name, item.enabled) for item in result.groups] == [("c-1", "North", True)]
    assert result.kept_days == 30


async def test_the_phone_is_only_asked_when_a_group_is_enabled():
    group = SimpleNamespace(chat="c-1", name="North", enabled=False)

    with _patch_phone([]) as phone_groups, _patch_store("set_group", return_value=group) as store:
        await update_group(map_id="map-1", group_id="c-1", change=ChatGroupChange(enabled=False), user=_user())

    phone_groups.assert_not_awaited()
    store.assert_awaited_once_with("map-1", "user-1", "c-1", False, False, [])


def _connector(answer):
    """The connector, answering every request with `answer` (a function of the request)."""
    client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    return patch("api.v2.routes.messages.httpx.AsyncClient", return_value=client)


async def _phone_groups_from(answer):
    from api.v2.routes.messages import _phone_groups

    with _connector(answer):
        return await _phone_groups("user-1")


async def test_the_groups_of_the_phone_come_from_the_connector():
    def answer(request):
        assert request.url.path == "/groups"
        assert request.url.params["session"] == "user-1"
        return httpx.Response(200, json=[{"chat": "hash-1", "name": "North"}])

    assert await _phone_groups_from(answer) == [{"chat": "hash-1", "name": "North"}]


def _down(request):
    raise httpx.ConnectError("down")


@pytest.mark.parametrize("answer", [
    _down,
    lambda request: httpx.Response(500),
    lambda request: httpx.Response(200, json=[{"name": "no chat"}]),
    lambda request: httpx.Response(200, json=[{"chat": "hash-1", "name": "x" * 201}]),
    lambda request: httpx.Response(200, json=[{"chat": "h" * 65, "name": "North"}]),
], ids=["does not answer", "fails", "not a list of groups", "name too long", "chat too long"])
async def test_a_connector_that_does_not_give_the_groups_is_told(answer):
    with pytest.raises(HTTPException) as raised:
        await _phone_groups_from(answer)

    assert raised.value.status_code == 502


async def test_a_connector_answer_too_big_is_not_read_to_the_end():
    from api.v2.routes.messages import MAX_PHONE_GROUPS_BYTES

    sent = []
    chunks_up_to_the_cap = MAX_PHONE_GROUPS_BYTES // 1024 + 1

    async def chunks():
        for _ in range(chunks_up_to_the_cap * 2):
            sent.append(1)
            yield b"x" * 1024

    with pytest.raises(HTTPException) as raised:
        await _phone_groups_from(lambda request: httpx.Response(200, content=chunks()))

    assert raised.value.status_code == 502
    assert len(sent) <= chunks_up_to_the_cap


@pytest.mark.parametrize("enabled", [True, False])
def test_the_routes_of_group_messages_are_there_only_with_the_switch_on(enabled):
    import importlib

    import api.v2

    try:
        with patch("settings.ENABLE_GROUP_MESSAGES", enabled):
            router = importlib.reload(api.v2).router
        paths = {route.path for route in router.routes}
        assert ("/v2/maps/{map_id}/messages" in paths) is enabled
        assert ("/v2/maps/{map_id}/groups" in paths) is enabled
        # The others are there either way
        assert "/v2/maps/{map_id}/keys" in paths
    finally:
        importlib.reload(api.v2)


async def test_a_time_without_zone_in_the_cursor_is_taken_as_utc():
    with _patch_store("messages", return_value=[]) as store:
        await read_messages(map_id="map-1", user=_user(), before=datetime(2026, 10, 22, 12), before_id="m-9")

    store.assert_awaited_once_with("map-1", "user-1", None, (datetime(2026, 10, 22, 12, tzinfo=UTC), "m-9"))


async def test_read_messages_of_a_map_the_user_does_not_own_is_not_found():
    with _patch_store("messages", side_effect=MapNotFound), pytest.raises(HTTPException) as raised:
        await read_messages(map_id="map-1", user=_user())

    assert raised.value.status_code == 404


async def test_read_messages_gives_each_one_with_the_pseudonym_of_its_group():
    message = SimpleNamespace(
        id="m-1", sender="s-1", text="closed", location=None, sent_at=datetime(2026, 10, 22, 12, tzinfo=UTC),
    )

    with _patch_store("messages", return_value=[(message, "c-1")]) as store:
        result = await read_messages(map_id="map-1", user=_user(), group_id="c-1")

    store.assert_awaited_once_with("map-1", "user-1", "c-1", None)
    assert [(item.id, item.group_id, item.text) for item in result.messages] == [("m-1", "c-1", "closed")]


async def test_the_next_page_needs_both_the_time_and_the_id_of_the_last_message():
    with pytest.raises(HTTPException) as raised:
        await read_messages(map_id="map-1", user=_user(), before=datetime(2026, 10, 22, tzinfo=UTC))

    assert raised.value.status_code == 422


def test_messages_are_kept_between_one_day_and_the_maximum():
    assert KeptDays(days=30).days == 30
    for days in (0, 91):
        with pytest.raises(ValidationError):
            KeptDays(days=days)
