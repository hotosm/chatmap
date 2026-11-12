from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DataError, MultipleResultsFound, OperationalError

from db import ChatGroup, GroupMessage, Map, MapKey, Point, PointTag, PointTagChange
from results.error import (
    AlreadyLinked,
    MapNotFound,
    MapNotLive,
    MessageDismissed,
    MessageLinked,
    StoreUnavailable,
    UnknownGroup,
    UnknownKey,
    UnknownMessage,
    UnknownPoint,
)
from store.group_messages_store import (
    MAX_TEXT_LENGTH,
    PRUNE_CHUNK,
    GroupMessagesStore,
    _prune,
    pseudonym,
)
from store.received_messages_store import ReceivedMessage


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.group_messages_store.session_scope", scope)


def _result(scalar=None, scalars=()):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar
    result.scalars.return_value = list(scalars)
    return result


def _map(owner_id="user-1", is_live=True):
    return Map(id="map-1", owner_id=owner_id, is_live=is_live, messages_kept_days=30)


def _message(text="", location="", chat="chat-1"):
    return ReceivedMessage.from_dict({
        "id": "1792682939000-0", "user": "device-1", "from": "sender-1", "chat": chat,
        "fromenc": "", "chatenc": "", "is_group": "1", "text": text, "date": "2026-10-22T12:00:00",
        "location": location, "photo": "", "video": "", "audio": "", "file": "",
    })


def _phone(*groups):
    return [{"chat": chat, "name": name} for chat, name in groups]


# ---- pseudonym ----

def test_a_pseudonym_tells_values_apart_within_a_map_without_saying_them():
    assert pseudonym("map-1", "chat-1") == pseudonym("map-1", "chat-1")
    assert pseudonym("map-1", "chat-1") != pseudonym("map-1", "chat-2")
    assert pseudonym("map-1", "chat-1") != pseudonym("map-2", "chat-1")
    assert "chat-1" not in pseudonym("map-1", "chat-1")


# ---- save ----

def _patch_thread():
    # The database is used from a thread; the tests run it right there
    async def run(function, *args):
        return function(*args)
    return patch("store.group_messages_store.asyncio.to_thread", run)


def _insert_result(kept):
    result = MagicMock()
    result.all.return_value = [(f"m-{i}",) for i in range(kept)]
    return result


# The groups of the tests were enabled long before their messages were sent
ENABLED_BEFORE = datetime(2026, 1, 1, tzinfo=UTC)


def _groups_result(rows):
    """The enabled groups among the chats of a batch: (chat, id), or (chat, id, enabled_at)."""
    result = MagicMock()
    result.all.return_value = [
        SimpleNamespace(chat=row[0], id=row[1], enabled_at=row[2] if len(row) > 2 else ENABLED_BEFORE)
        for row in rows
    ]
    return result


async def test_messages_without_text_nor_location_are_not_kept():
    db = MagicMock()

    with _patch_scope(db), _patch_thread():
        assert await GroupMessagesStore.save("device-1", [_message()]) == 0
    db.execute.assert_not_called()


async def test_a_message_that_cannot_be_read_is_skipped_without_holding_back_the_others():
    db = MagicMock()
    db.execute.side_effect = [
        _result(scalar="map-1"), _groups_result([(pseudonym("map-1", "chat-1"), "group-1")]), _insert_result(1),
    ]
    unreadable_date = _message(location="-34.6,-58.4")
    unreadable_date.date = "not a date"

    with _patch_scope(db), _patch_thread():
        kept = await GroupMessagesStore.save("device-1", [unreadable_date, _message(location="-34.6,-58.4")])

    assert kept == 1
    assert len(db.execute.call_args_list[2].args[0].compile().params) > 0


async def test_nothing_is_kept_without_a_live_map():
    db = MagicMock()
    db.execute.return_value = _result(scalar=None)

    with _patch_scope(db), _patch_thread():
        assert await GroupMessagesStore.save("device-1", [_message(location="-34.6,-58.4")]) == 0
    db.commit.assert_not_called()


async def test_a_batch_is_kept_in_one_insert_only_for_the_groups_the_map_listens_to():
    db = MagicMock()
    # The live map, the enabled groups among the chats of the batch, the insert
    db.execute.side_effect = [
        _result(scalar="map-1"), _groups_result([(pseudonym("map-1", "chat-1"), "group-1")]), _insert_result(2),
    ]
    batch = [_message(text="a"), _message(text="b"), _message(text="c", chat="chat-2")]

    with _patch_scope(db), _patch_thread(), patch("store.group_messages_store.decrypt_message", side_effect=str.upper):
        assert await GroupMessagesStore.save("device-1", batch) == 2

    assert db.execute.call_count == 3
    rows = db.execute.call_args_list[2].args[0].compile().params
    assert [rows[f"text_m{i}"] for i in range(2)] == ["A", "B"]
    assert rows["group_id_m0"] == "group-1"
    assert rows["sender_m0"] == pseudonym("map-1", "sender-1")
    assert rows["sent_at_m0"] == datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    db.commit.assert_called_once()


async def test_nothing_said_before_a_group_was_enabled_is_kept():
    db = MagicMock()
    # The messages of the tests are sent at 12:00:00, in whole seconds
    enabled_at = datetime(2026, 10, 22, 12, 0, 0, 500000, tzinfo=UTC)
    db.execute.side_effect = [
        _result(scalar="map-1"),
        _groups_result([
            (pseudonym("map-1", "chat-1"), "group-1", enabled_at),
            (pseudonym("map-1", "chat-2"), "group-2", datetime(2026, 10, 22, 12, 0, 1, tzinfo=UTC)),
        ]),
        _insert_result(1),
    ]
    batch = [_message(text="a"), _message(text="b", chat="chat-2")]

    with _patch_scope(db), _patch_thread(), patch("store.group_messages_store.decrypt_message", side_effect=str.upper):
        assert await GroupMessagesStore.save("device-1", batch) == 1

    rows = db.execute.call_args_list[2].args[0].compile().params
    assert rows["group_id_m0"] == "group-1"
    assert "group_id_m1" not in rows


async def test_the_messages_of_an_owner_with_more_than_one_live_map_are_kept_in_none():
    db = MagicMock()
    db.execute.side_effect = MultipleResultsFound()

    with _patch_scope(db), _patch_thread():
        assert await GroupMessagesStore.save("device-1", [_message(location="-34.6,-58.4")]) == 0
    db.commit.assert_not_called()


async def test_nul_characters_are_taken_out_since_postgres_does_not_take_them():
    db = MagicMock()
    db.execute.side_effect = [
        _result(scalar="map-1"), _groups_result([(pseudonym("map-1", "chat-1"), "group-1")]), _insert_result(1),
    ]

    with _patch_scope(db), _patch_thread(), patch("store.group_messages_store.decrypt_message", return_value="clo\x00sed"):
        await GroupMessagesStore.save("device-1", [_message(text="x", location="1\x00,2")])

    params = db.execute.call_args_list[2].args[0].compile().params
    assert (params["text_m0"], params["location_m0"]) == ("closed", "1,2")


async def test_a_batch_the_database_does_not_take_is_kept_one_by_one_skipping_the_bad_message():
    db = MagicMock()
    db.execute.side_effect = [
        _result(scalar="map-1"), _groups_result([(pseudonym("map-1", "chat-1"), "group-1")]),
        DataError("insert", {}, Exception()),            # the whole batch
        _insert_result(1), DataError("insert", {}, Exception()), _insert_result(1),  # one by one
    ]
    batch = [_message(text="a"), _message(text="b"), _message(text="c")]

    with _patch_scope(db), _patch_thread(), patch("store.group_messages_store.decrypt_message", side_effect=str.upper):
        assert await GroupMessagesStore.save("device-1", batch) == 2


async def test_a_database_that_does_not_answer_is_tried_again_later():
    db = MagicMock()
    db.execute.side_effect = [
        _result(scalar="map-1"), _groups_result([(pseudonym("map-1", "chat-1"), "group-1")]),
        OperationalError("insert", {}, Exception()),
    ]

    with _patch_scope(db), _patch_thread(), pytest.raises(StoreUnavailable):
        await GroupMessagesStore.save("device-1", [_message(location="1,2")])


def test_a_batch_is_one_insert_that_skips_messages_already_kept():
    from store.group_messages_store import _insert
    db = MagicMock()

    _insert(db, [{"map_id": "map-1", "stream_id": "1-0"}])

    sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (map_id, stream_id) DO NOTHING" in sql


def test_old_messages_go_a_chunk_at_a_time():
    db = MagicMock()
    db.execute.side_effect = [MagicMock(rowcount=PRUNE_CHUNK), MagicMock(rowcount=PRUNE_CHUNK), MagicMock(rowcount=3)]

    with _patch_scope(db):
        assert _prune() == 2 * PRUNE_CHUNK + 3

    assert db.commit.call_count == 3
    sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "make_interval" in sql and "LIMIT" in sql


async def test_a_long_text_is_cut():
    db = MagicMock()
    db.execute.side_effect = [
        _result(scalar="map-1"), _groups_result([(pseudonym("map-1", "chat-1"), "group-1")]), _insert_result(1),
    ]

    with _patch_scope(db), _patch_thread(), patch("store.group_messages_store.decrypt_message", return_value="x" * 5000):
        await GroupMessagesStore.save("device-1", [_message(text="long")])

    assert len(db.execute.call_args_list[2].args[0].compile().params["text_m0"]) == MAX_TEXT_LENGTH


# ---- groups ----

async def test_only_the_owner_of_a_live_map_sees_its_groups():
    db = MagicMock()

    db.get.return_value = _map(owner_id="someone-else")
    with _patch_scope(db), pytest.raises(MapNotFound):
        await GroupMessagesStore.groups("map-1", "user-1", [])

    db.get.return_value = _map(is_live=False)
    with _patch_scope(db), pytest.raises(MapNotLive):
        await GroupMessagesStore.groups("map-1", "user-1", [])


async def test_the_groups_of_the_phone_say_which_ones_the_map_listens_to():
    db = MagicMock()
    db.get.return_value = _map()
    listened = ChatGroup(chat=pseudonym("map-1", "chat-1"), name="North", enabled=True)
    left = ChatGroup(chat=pseudonym("map-1", "chat-9"), name="Old", enabled=False)
    db.execute.return_value = _result(scalars=[listened, left])

    with _patch_scope(db):
        groups, kept_days = await GroupMessagesStore.groups(
            "map-1", "user-1", _phone(("chat-1", "North"), ("chat-2", "South")),
        )

    # The ones of the phone first, then the ones the map keeps that the phone left
    assert [(group.name, group.enabled) for group in groups] == [("North", True), ("South", False), ("Old", False)]
    assert groups[1].chat == pseudonym("map-1", "chat-2")
    assert kept_days == 30


# ---- set_group ----

async def test_enabling_a_group_keeps_its_name_from_the_phone():
    db = MagicMock()
    db.get.return_value = _map()
    created = ChatGroup(map_id="map-1", chat=pseudonym("map-1", "chat-1"), name="North", enabled=True)
    created_result = MagicMock()
    created_result.scalar_one.return_value = created
    # Not there yet, the insert (nothing if two enables race), then the group
    db.execute.side_effect = [_result(scalar=None), MagicMock(), created_result]

    with _patch_scope(db):
        group = await GroupMessagesStore.set_group(
            "map-1", "user-1", pseudonym("map-1", "chat-1"), True, False, _phone(("chat-1", "North")),
        )

    insert = db.execute.call_args_list[1].args[0].compile(dialect=postgresql.dialect())
    assert "ON CONFLICT (map_id, chat) DO NOTHING" in str(insert)
    assert insert.params["name"] == "North"
    assert (group.name, group.enabled) == ("North", True)


async def test_a_group_enabled_again_keeps_what_is_said_from_then_on():
    db = MagicMock()
    db.get.return_value = _map()
    group = ChatGroup(id="group-1", chat=pseudonym("map-1", "chat-1"), name="North", enabled=False,
                      enabled_at=ENABLED_BEFORE)
    db.execute.return_value = _result(scalar=group)

    with _patch_scope(db):
        await GroupMessagesStore.set_group(
            "map-1", "user-1", group.chat, True, False, _phone(("chat-1", "North")),
        )
    assert group.enabled is True
    assert str(group.enabled_at) == "now()"

    # Enabling it while it is enabled does not move the time
    group.enabled_at = ENABLED_BEFORE
    with _patch_scope(db):
        await GroupMessagesStore.set_group(
            "map-1", "user-1", group.chat, True, False, _phone(("chat-1", "North")),
        )
    assert group.enabled_at == ENABLED_BEFORE


async def test_a_group_the_phone_does_not_have_cannot_be_enabled():
    db = MagicMock()
    db.get.return_value = _map()
    db.execute.return_value = _result(scalar=None)

    with _patch_scope(db), pytest.raises(UnknownGroup):
        await GroupMessagesStore.set_group("map-1", "user-1", "unknown", True, False, _phone(("chat-1", "North")))


async def test_disabling_a_group_keeps_its_messages_unless_asked():
    db = MagicMock()
    db.get.return_value = _map()
    group = ChatGroup(id="group-1", chat="c-1", name="North", enabled=True)
    db.execute.return_value = _result(scalar=group)

    with _patch_scope(db):
        await GroupMessagesStore.set_group("map-1", "user-1", "c-1", False, False, [])
    assert group.enabled is False
    assert db.execute.call_count == 1

    group.enabled = True
    with _patch_scope(db):
        await GroupMessagesStore.set_group("map-1", "user-1", "c-1", False, True, [])
    deleted = db.execute.call_args_list[-1].args[0]
    assert str(deleted).startswith("DELETE FROM group_messages")


# ---- set_kept_days ----

async def test_the_owner_of_a_live_map_sets_how_many_days_its_messages_are_kept():
    db = MagicMock()
    map_obj = _map()
    db.get.return_value = map_obj

    with _patch_scope(db):
        assert await GroupMessagesStore.set_kept_days("map-1", "user-1", 7) == 7
    assert map_obj.messages_kept_days == 7


# ---- messages ----

async def test_the_messages_of_a_map_are_only_for_its_owner():
    db = MagicMock()
    db.get.return_value = _map(owner_id="someone-else")

    with _patch_scope(db), pytest.raises(MapNotFound):
        await GroupMessagesStore.messages("map-1", "user-1")


async def test_the_messages_of_a_map_are_the_ones_of_the_groups_it_listens_to_newest_first():
    db = MagicMock()
    db.get.return_value = _map()
    db.execute.return_value = []

    with _patch_scope(db):
        await GroupMessagesStore.messages("map-1", "user-1", chat="c-1")

    query = str(db.execute.call_args.args[0])
    assert "chat_groups.enabled" in query
    assert "group_messages.dismissed_at IS NULL" in query
    assert "chat_groups.chat = " in query
    assert "ORDER BY group_messages.sent_at DESC, group_messages.id DESC" in query


async def test_a_message_is_linked_only_to_points_still_in_its_map():
    db = MagicMock()
    db.get.return_value = _map()
    db.execute.return_value = []

    with _patch_scope(db):
        await GroupMessagesStore.messages("map-1", "user-1", state="linked")

    query = str(db.execute.call_args.args[0])
    assert "point_tag_changes.undone_at IS NULL" in query
    assert "points.map_id = group_messages.map_id" in query


async def test_the_next_page_goes_after_the_time_and_id_of_the_last_message():
    db = MagicMock()
    db.get.return_value = _map()
    db.execute.return_value = []

    with _patch_scope(db):
        await GroupMessagesStore.messages("map-1", "user-1", before=(datetime(2026, 10, 22, tzinfo=UTC), "m-9"))

    assert "(group_messages.sent_at, group_messages.id) < (" in str(db.execute.call_args.args[0])


# ---- link, set_dismissed ----

SENT_AT = datetime(2026, 10, 22, 12, tzinfo=UTC)
STATUS = MapKey(id="k-1", map_id="map-1", key="Status", single=True, closed=True)


def _group_message(dismissed_at=None):
    return GroupMessage(id="m-1", map_id="map-1", group_id="g-1", sent_at=SENT_AT, dismissed_at=dismissed_at)


def _point(map_id="map-1", removed=False, place=True):
    return SimpleNamespace(Point=Point(id="p-1", map_id=map_id, removed=removed, place=place), owner_id="user-1")


def _patch_link(message=None, point=None, key=STATUS, twice=None, given=None):
    """A message of the user, a point and a key it can link, and what give_tag answers."""
    db = MagicMock()
    db.get.return_value = key
    db.execute.return_value.scalars.return_value.first.return_value = twice
    patches = (
        _patch_scope(db),
        patch("store.group_messages_store._owned_message", return_value=message or _group_message()),
        patch("store.group_messages_store.lock_point", return_value=point or _point()),
        patch("store.group_messages_store.give_tag", return_value=given or (_tag_change(), [_point_tag()])),
    )
    return db, patches


def _tag_change(value_id="v-1"):
    return PointTagChange(id=7, point_id="p-1", key_id="k-1", value_id=value_id, value="Closed", happened_at=SENT_AT)


def _point_tag(value_id="v-1", confirmed_at=SENT_AT):
    return PointTag(point_id="p-1", key_id="k-1", value_id=value_id, since=confirmed_at, confirmed_at=confirmed_at)


async def _link(patches, **kwargs):
    with patches[0], patches[1], patches[2], patches[3] as give:
        result = await GroupMessagesStore.link("m-1", "user-1", "p-1", kwargs.get("key_id", "k-1"), value_id="v-1")
    return result, give


async def test_a_link_gives_the_value_at_the_time_of_the_message():
    db, patches = _patch_link()

    (change, tags, applied), give = await _link(patches)

    give.assert_called_once_with(
        db, "p-1", STATUS, "set", "v-1", None, SENT_AT, "user-1", source="message", message_id="m-1",
    )
    db.commit.assert_called_once()
    assert (change.id, applied) == (7, True)


async def test_a_message_older_than_what_the_point_has_only_goes_to_its_history():
    newer = _point_tag(value_id="v-2", confirmed_at=datetime(2026, 10, 22, 13, tzinfo=UTC))
    _, patches = _patch_link(given=(_tag_change(), [newer]))

    (_, tags, applied), _ = await _link(patches)

    assert ([tag.value_id for tag in tags], applied) == (["v-2"], False)


@pytest.mark.parametrize("point", [_point(map_id="map-2"), _point(removed=True), _point(place=False)])
async def test_a_message_only_links_to_points_of_its_map_that_are_not_removed(point):
    _, patches = _patch_link(point=point)

    with pytest.raises(UnknownPoint):
        await _link(patches)


async def test_a_message_does_not_link_to_a_key_of_another_map():
    _, patches = _patch_link(key=MapKey(id="k-9", map_id="map-2", key="Status", single=True, closed=True))

    with pytest.raises(UnknownKey):
        await _link(patches)


async def test_a_dismissed_message_is_not_linked():
    _, patches = _patch_link(message=_group_message(dismissed_at=SENT_AT))

    with pytest.raises(MessageDismissed):
        await _link(patches)


async def test_the_same_link_twice_is_refused():
    db, patches = _patch_link(twice=7)

    with pytest.raises(AlreadyLinked):
        await _link(patches)
    db.commit.assert_not_called()


def _patch_dismiss(message, linked=False):
    db = MagicMock()
    db.execute.return_value.scalar.return_value = linked
    db.get.return_value = ChatGroup(id="g-1", chat="c-1")
    return db, (
        _patch_scope(db),
        patch("store.group_messages_store._owned_message", return_value=message),
        patch("store.group_messages_store._links_of", return_value={}),
    )


async def test_a_message_is_dismissed_and_brought_back():
    message = _group_message()
    db, (scope, owned, links) = _patch_dismiss(message)

    with scope, owned, links:
        dismissed, chat, _ = await GroupMessagesStore.set_dismissed("m-1", "user-1", True)
    assert dismissed.dismissed_at is not None and chat == "c-1"

    with scope, owned, links:
        back, _, _ = await GroupMessagesStore.set_dismissed("m-1", "user-1", False)
    assert back.dismissed_at is None


async def test_a_linked_message_is_not_dismissed():
    db, (scope, owned, links) = _patch_dismiss(_group_message(), linked=True)

    with scope, owned, links, pytest.raises(MessageLinked):
        await GroupMessagesStore.set_dismissed("m-1", "user-1", True)
    db.commit.assert_not_called()


async def test_a_message_of_another_user_or_of_a_group_not_listened_to_does_not_exist():
    db = MagicMock()
    db.execute.return_value.one_or_none.side_effect = [
        None,
        SimpleNamespace(GroupMessage=_group_message(), owner_id="user-2", enabled=True),
        SimpleNamespace(GroupMessage=_group_message(), owner_id="user-1", enabled=False),
    ]

    for _ in range(3):
        with _patch_scope(db), pytest.raises(UnknownMessage):
            await GroupMessagesStore.set_dismissed("m-1", "user-1", True)
