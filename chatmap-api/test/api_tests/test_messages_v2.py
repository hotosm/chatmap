from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from api.v2.routes.messages import (
    link_message,
    read_groups,
    read_messages,
    update_group,
    update_group_points,
    update_message,
)
from api.v2.schemas.messages import (
    ChatGroupChange,
    GroupPlaces,
    KeptDays,
    LinkRequest,
    MessageChange,
)
from results.error import (
    AlreadyLinked,
    MapNotFound,
    MapNotLive,
    MessageLinked,
    TooManyPlaces,
    UnknownGroup,
    UnknownMessage,
    UnknownPoint,
)


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.messages.GroupMessagesStore.{method}", AsyncMock(**kwargs))


def _patch_phone(groups):
    return patch("api.v2.routes.messages._phone_groups", AsyncMock(return_value=groups))


async def test_read_groups_asks_the_connector_for_the_groups_of_the_phone_of_the_user():
    phone = [{"chat": "hash-1", "name": "North"}]
    group = SimpleNamespace(id="g-1", chat="c-1", name="North", enabled=True)
    places = {"g-1": ["p-1", "p-2"]}

    with _patch_phone(phone) as phone_groups, _patch_store("groups", return_value=([group], places, 30)) as store:
        result = await read_groups(map_id="map-1", user=_user())

    phone_groups.assert_awaited_once_with("user-1")
    store.assert_awaited_once_with("map-1", "user-1", phone)
    assert [(item.id, item.name, item.enabled, item.point_ids) for item in result.groups] == [
        ("c-1", "North", True, ["p-1", "p-2"]),
    ]
    assert result.kept_days == 30


async def test_the_phone_is_only_asked_when_a_group_is_enabled():
    group = SimpleNamespace(chat="c-1", name="North", enabled=False)

    with _patch_phone([]) as phone_groups, _patch_store("set_group", return_value=(group, [])) as store:
        await update_group(map_id="map-1", group_id="c-1", change=ChatGroupChange(enabled=False), user=_user())

    phone_groups.assert_not_awaited()
    store.assert_awaited_once_with("map-1", "user-1", "c-1", False, False, [])


@pytest.mark.parametrize("error, status_code", [
    (MapNotFound(), 404), (MapNotLive(), 409), (UnknownGroup("c-1"), 404),
    (UnknownPoint("p-9"), 404), (TooManyPlaces(2), 422),
])
async def test_setting_the_places_of_a_group_tells_what_failed(error, status_code):
    places = GroupPlaces(point_ids=["p-9"])

    with _patch_store("set_group_points", side_effect=error), pytest.raises(HTTPException) as raised:
        await update_group_points(map_id="map-1", group_id="c-1", places=places, user=_user())

    assert raised.value.status_code == status_code


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
        assert ("/v2/maps/{map_id}/groups/{group_id}/points" in paths) is enabled
        # The others are there either way
        assert "/v2/maps/{map_id}/keys" in paths
    finally:
        importlib.reload(api.v2)


# When what was reviewed is taken, as the first page gives it
AS_OF = datetime(2026, 10, 22, 13, tzinfo=UTC)


async def test_a_time_without_zone_in_the_cursor_is_taken_as_utc():
    with _patch_store("messages", return_value=([], {}, AS_OF)) as store:
        await read_messages(
            map_id="map-1", user=_user(), before=datetime(2026, 10, 22, 12), before_id="m-9", before_rank=1,
            as_of=datetime(2026, 10, 22, 13),
        )

    store.assert_awaited_once_with(
        "map-1", "user-1", None, (1, datetime(2026, 10, 22, 12, tzinfo=UTC), "m-9"), None, AS_OF,
    )


async def test_the_next_page_of_a_read_newest_first_goes_after_the_time_and_id_only():
    with _patch_store("messages", return_value=([], {}, AS_OF)) as store:
        await read_messages(
            map_id="map-1", user=_user(), before=datetime(2026, 10, 22, 12, tzinfo=UTC), before_id="m-9", state="linked",
        )

    assert store.await_args.args[3] == (datetime(2026, 10, 22, 12, tzinfo=UTC), "m-9")


@pytest.mark.parametrize("cursor", [
    # The next page of all of them or the new ones needs where the last one is in the order
    {"before": datetime(2026, 10, 22, tzinfo=UTC), "before_id": "m-9"},
    {"before_rank": 1},
    {"before_rank": 1, "state": "new"},
    # A read newest first has no ranks
    {"before": datetime(2026, 10, 22, tzinfo=UTC), "before_id": "m-9", "before_rank": 1, "state": "linked"},
])
async def test_the_parts_of_the_cursor_go_together(cursor):
    with _patch_store("messages") as store, pytest.raises(HTTPException) as raised:
        await read_messages(map_id="map-1", user=_user(), **cursor)

    assert raised.value.status_code == 422
    store.assert_not_awaited()


async def test_read_messages_of_a_map_the_user_does_not_own_is_not_found():
    with _patch_store("messages", side_effect=MapNotFound), pytest.raises(HTTPException) as raised:
        await read_messages(map_id="map-1", user=_user())

    assert raised.value.status_code == 404


async def test_read_messages_gives_each_one_with_the_pseudonym_of_its_group():
    with _patch_store("messages", return_value=([(_message(), "c-1", 1)], {}, AS_OF)) as store:
        result = await read_messages(map_id="map-1", user=_user(), group_id="c-1")

    store.assert_awaited_once_with("map-1", "user-1", "c-1", None, None, None)
    assert [(item.id, item.group_id, item.text, item.links) for item in result.messages] == [("m-1", "c-1", "closed", [])]


def _message(dismissed_at=None, **changes):
    return SimpleNamespace(**{
        "id": "m-1", "sender": "s-1", "text": "closed", "location": None,
        "sent_at": datetime(2026, 10, 22, 12, tzinfo=UTC), "dismissed_at": dismissed_at, **changes,
    })


def _change(change_id=7, undone_at=None):
    return SimpleNamespace(
        id=change_id, point_id="p-1", key_id="k-1", value_id="v-1", value="Closed", undone_at=undone_at,
    )


async def test_read_messages_gives_the_values_each_one_gave_to_points():
    links = {"m-1": [_change(8), _change(7, undone_at=datetime(2026, 10, 23, tzinfo=UTC))]}

    with _patch_store("messages", return_value=([(_message(), "c-1", None)], links, AS_OF)):
        result = await read_messages(map_id="map-1", user=_user(), state="linked")

    assert [(link.change_id, link.point_id, link.value, link.undone) for link in result.messages[0].links] == [
        (8, "p-1", "Closed", False), (7, "p-1", "Closed", True),
    ]


# ---- POST /v2/messages/{id}/links, PUT /v2/messages/{id} ----

async def test_linking_a_message_gives_the_value_to_the_point_and_says_whether_it_has_it_now():
    tag = SimpleNamespace(
        point_id="p-1", key_id="k-1", value_id="v-2", value=None,
        since=datetime(2026, 10, 22, 13, tzinfo=UTC), confirmed_at=datetime(2026, 10, 22, 13, tzinfo=UTC),
    )
    link = LinkRequest(point_id="p-1", key_id="k-1", value_id="v-1")

    with _patch_store("link", return_value=(_change(), [tag], False)) as store:
        result = await link_message(message_id="m-1", link=link, user=_user())

    store.assert_awaited_once_with("m-1", "user-1", "p-1", "k-1", value_id="v-1", value=None)
    assert (result.link.change_id, result.applied, [item.value_id for item in result.tags]) == (7, False, ["v-2"])


@pytest.mark.parametrize("error, status_code", [
    (UnknownMessage("m-1"), 404), (UnknownPoint("p-1"), 404), (AlreadyLinked(7), 409),
])
async def test_linking_tells_what_failed(error, status_code):
    link = LinkRequest(point_id="p-1", key_id="k-1", value_id="v-1")

    with _patch_store("link", side_effect=error), pytest.raises(HTTPException) as raised:
        await link_message(message_id="m-1", link=link, user=_user())

    assert raised.value.status_code == status_code


def test_a_free_value_of_a_link_is_trimmed():
    assert LinkRequest(point_id="p-1", key_id="k-2", value="  near the school ").value == "near the school"
    with pytest.raises(ValidationError):
        LinkRequest(point_id="p-1", key_id="k-2", value=" ")


async def test_dismissing_a_message_gives_it_back_dismissed():
    dismissed_at = datetime(2026, 10, 23, tzinfo=UTC)

    with _patch_store("set_dismissed", return_value=(_message(dismissed_at), "c-1", [])) as store:
        result = await update_message(message_id="m-1", change=MessageChange(dismissed=True), user=_user())

    store.assert_awaited_once_with("m-1", "user-1", True)
    assert (result.id, result.group_id, result.dismissed_at) == ("m-1", "c-1", dismissed_at)


async def test_a_linked_message_is_not_dismissed():
    with _patch_store("set_dismissed", side_effect=MessageLinked("m-1")), pytest.raises(HTTPException) as raised:
        await update_message(message_id="m-1", change=MessageChange(dismissed=True), user=_user())

    assert raised.value.status_code == 409


async def test_the_next_page_needs_both_the_time_and_the_id_of_the_last_message():
    with pytest.raises(HTTPException) as raised:
        await read_messages(map_id="map-1", user=_user(), before=datetime(2026, 10, 22, tzinfo=UTC))

    assert raised.value.status_code == 422


def test_messages_are_kept_between_one_day_and_the_maximum():
    assert KeptDays(days=30).days == 30
    for days in (0, 91):
        with pytest.raises(ValidationError):
            KeptDays(days=days)
