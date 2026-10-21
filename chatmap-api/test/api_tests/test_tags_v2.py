from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from api.v2.routes.tags import read_history, read_tags, set_point_tag, undo_change
from api.v2.schemas.tags import TagChangeRequest

SINCE = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
CONFIRMED = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)
HAPPENED_AT = datetime(2026, 10, 6, 8, 30, tzinfo=UTC)
RECORDED_AT = datetime(2026, 10, 6, 8, 45, tzinfo=UTC)


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _tag(point_id="p-1", key_id="k-1", value_id="v-1", value=None):
    return SimpleNamespace(
        point_id=point_id, key_id=key_id, value_id=value_id, value=value, since=SINCE, confirmed_at=CONFIRMED,
    )


def _change(change_id=1, action="set", value_id="v-1", value="Open", undone_at=None, undone_by=None):
    return SimpleNamespace(
        id=change_id, action=action, value_id=value_id, value=value, happened_at=HAPPENED_AT,
        recorded_at=RECORDED_AT, source="manual", user_id="user-1", undone_at=undone_at, undone_by=undone_by,
    )


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.tags.PointTagsStore.{method}", AsyncMock(**kwargs))


# ---- GET /v2/maps/{map_id}/tags, PUT /v2/points/{point_id}/tags/{key_id} ----

async def test_read_tags_returns_what_each_point_has():
    with _patch_store("read_tags", return_value=[_tag(), _tag(key_id="k-2", value_id=None, value="near the school")]):
        result = await read_tags(map_id="map-1", user=None)

    assert [(tag.point_id, tag.key_id, tag.value_id, tag.value) for tag in result.tags] == [
        ("p-1", "k-1", "v-1", None), ("p-1", "k-2", None, "near the school"),
    ]
    assert (result.tags[0].since, result.tags[0].confirmed_at) == (SINCE, CONFIRMED)


async def test_set_point_tag_passes_the_change():
    change = TagChangeRequest(value_id="v-1", happened_at=HAPPENED_AT)

    with _patch_store("set_point_tag", return_value=[_tag()]) as store:
        result = await set_point_tag(point_id="p-1", key_id="k-1", change=change, user=_user())

    store.assert_awaited_once_with(
        "p-1", "k-1", "user-1", "set", value_id="v-1", value=None, happened_at=HAPPENED_AT,
    )
    assert [tag.value_id for tag in result.tags] == ["v-1"]


# ---- GET /v2/points/{point_id}/history, POST /v2/tag-changes/{change_id}/undo ----

async def test_history_returns_the_changes_with_their_key():
    rows = [(_change(2, "remove", None, None), "Status"), (_change(1), "Status")]

    with _patch_store("history", return_value=rows) as store:
        result = await read_history(point_id="p-1", user=_user())

    store.assert_awaited_once_with("p-1", "user-1")
    assert [(change.id, change.key, change.action, change.value) for change in result.changes] == [
        (2, "Status", "remove", None), (1, "Status", "set", "Open"),
    ]
    assert (result.changes[1].happened_at, result.changes[1].recorded_at) == (HAPPENED_AT, RECORDED_AT)


async def test_undo_marks_the_change_and_returns_it():
    undone_at = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)

    with _patch_store("set_undone", return_value=(_change(undone_at=undone_at, undone_by="user-1"), "Status")) as store:
        result = await undo_change(change_id=1, user=_user())

    store.assert_awaited_once_with(1, "user-1", True)
    assert (result.id, result.key, result.undone_at, result.undone_by) == (1, "Status", undone_at, "user-1")


# ---- what a change may be ----

def test_a_free_value_is_trimmed_and_has_a_maximum_length():
    assert TagChangeRequest(value="  near the school ").value == "near the school"
    with pytest.raises(ValidationError):
        TagChangeRequest(value="x" * 101)


def test_a_change_cannot_happen_in_a_time_to_come():
    with pytest.raises(ValidationError):
        TagChangeRequest(value_id="v-1", happened_at=datetime.now(UTC) + timedelta(hours=1))


def test_a_time_without_zone_is_taken_as_utc():
    change = TagChangeRequest(value_id="v-1", happened_at=datetime(2026, 10, 6, 8, 30))

    assert change.happened_at == datetime(2026, 10, 6, 8, 30, tzinfo=UTC)
