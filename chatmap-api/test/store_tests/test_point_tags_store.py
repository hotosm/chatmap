from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from db import MapKey, MapKeyValue, Point, PointTag
from results.error import ArchivedValue, InvalidTagValue, NotAuthorized, UnknownKey, UnknownTagChange, UnknownValue
from store.point_tags_store import PointTagsStore, _give_tag

STATUS = MapKey(id="k-1", map_id="map-1", key="Status", single=True, closed=True)
NOTES = MapKey(id="k-2", map_id="map-1", key="Notes", single=False, closed=False)


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.point_tags_store.session_scope", scope)


def _db(option=None, current=()):
    """A session that finds this option and the tags the point has now."""
    db = MagicMock()
    db.get.return_value = option
    db.execute.return_value.scalars.return_value = list(current)
    return db


def _give(db, key=STATUS, action="set", value_id=None, value=None):
    with patch("store.point_tags_store.record_change") as record:
        _give_tag(db, "p-1", key, action, value_id, value, None, "user-1")
    return record


# ---- _give_tag ----

def test_a_key_with_a_list_needs_one_of_its_values():
    with pytest.raises(InvalidTagValue):
        _give(_db(), value="Open")
    with pytest.raises(InvalidTagValue):
        _give(_db())


def test_a_value_of_another_key_is_not_taken():
    with pytest.raises(UnknownValue):
        _give(_db(option=MapKeyValue(id="v-9", key_id="k-9")), value_id="v-9")


def test_an_archived_value_is_not_given():
    archived = MapKeyValue(id="v-1", key_id="k-1", archived_at=datetime(2026, 10, 6, tzinfo=UTC))

    with pytest.raises(ArchivedValue):
        _give(_db(option=archived), value_id="v-1")


def test_a_free_key_takes_a_text():
    with pytest.raises(InvalidTagValue):
        _give(_db(), key=NOTES, value_id="v-1")


def test_a_value_of_the_list_is_written_down():
    option = MapKeyValue(id="v-1", key_id="k-1", value="Open")

    record = _give(_db(option=option), value_id="v-1")

    record.assert_called_once()
    assert record.call_args.kwargs["option"] is option


def test_taking_out_what_the_point_does_not_have_writes_nothing():
    record = _give(_db(current=[]), action="remove")

    record.assert_not_called()


def test_taking_out_a_value_the_point_does_not_have_writes_nothing():
    current = [PointTag(point_id="p-1", key_id="k-1", value_id="v-1")]
    other = MapKeyValue(id="v-2", key_id="k-1")

    assert not _give(_db(option=other, current=current), action="remove", value_id="v-2").called


def test_taking_out_a_free_value_needs_the_one_the_point_has():
    current = [PointTag(point_id="p-1", key_id="k-2", value="near the school")]

    assert not _give(_db(current=current), key=NOTES, action="remove", value="other").called
    assert _give(_db(current=current), key=NOTES, action="remove", value="near the school").called


# ---- PointTagsStore ----

def _db_point(owner_id="user-1", key=STATUS):
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = SimpleNamespace(
        Point=Point(id="p-1", map_id="map-1"), owner_id=owner_id,
    )
    db.get.return_value = key
    return db


async def test_only_the_owner_gives_tags():
    with _patch_scope(_db_point(owner_id="someone-else")), pytest.raises(NotAuthorized):
        await PointTagsStore.set_point_tag("p-1", "k-1", "user-1", "set", value_id="v-1")


async def test_a_point_does_not_take_a_key_of_another_map():
    other = MapKey(id="k-9", map_id="map-2", single=True, closed=True)

    with _patch_scope(_db_point(key=other)), pytest.raises(UnknownKey):
        await PointTagsStore.set_point_tag("p-1", "k-9", "user-1", "set", value_id="v-1")


async def test_only_the_owner_sees_the_history():
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = "someone-else"

    with _patch_scope(db), pytest.raises(NotAuthorized):
        await PointTagsStore.history("p-1", "user-1")


async def test_undoing_an_unknown_change_fails():
    db = MagicMock()
    db.get.return_value = None

    with _patch_scope(db), pytest.raises(UnknownTagChange):
        await PointTagsStore.set_undone(999, "user-1", True)


async def test_a_change_of_a_map_the_point_was_in_before_does_not_come_back():
    # The point moved to map-1; the change is of a key of its old map
    db = _db_point(key=MapKey(id="k-9", map_id="map-2"))
    db.get.side_effect = [SimpleNamespace(point_id="p-1", key_id="k-9"), MapKey(id="k-9", map_id="map-2")]

    with _patch_scope(db), pytest.raises(UnknownTagChange):
        await PointTagsStore.set_undone(1, "user-1", True)
