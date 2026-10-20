from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.v2.routes.tag_changes import read_history, undo_change
from results.error import NotAuthorized, StoreUnavailable, UnknownTagChange

HAPPENED_AT = datetime(2026, 10, 6, 8, 30, tzinfo=UTC)
RECORDED_AT = datetime(2026, 10, 6, 8, 45, tzinfo=UTC)


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _change(change_id=1, action="set", value_id="s-1", value="Open", undone_at=None, undone_by=None):
    return SimpleNamespace(
        id=change_id, action=action, value_id=value_id, value=value, happened_at=HAPPENED_AT,
        recorded_at=RECORDED_AT, source="manual", user_id="user-1", undone_at=undone_at, undone_by=undone_by,
    )


def _patch_store(method, **kwargs):
    return patch(f"api.v2.routes.tag_changes.PointTagsStore.{method}", AsyncMock(**kwargs))


# ---- GET /v2/points/{point_id}/history ----

async def test_history_returns_the_changes_with_their_key():
    rows = [(_change(2, "remove", None, None), "status"), (_change(1), "status")]

    with _patch_store("history", return_value=rows) as store:
        result = await read_history(point_id="p-1", user=_user())

    store.assert_awaited_once_with("p-1", "user-1")
    assert [(change.id, change.key, change.action, change.value) for change in result.changes] == [
        (2, "status", "remove", None), (1, "status", "set", "Open"),
    ]
    assert result.changes[1].happened_at == HAPPENED_AT
    assert result.changes[1].recorded_at == RECORDED_AT


@pytest.mark.parametrize("error, status_code", [(NotAuthorized(), 403), (StoreUnavailable(), 503)])
async def test_history_maps_store_errors_to_http(error, status_code):
    with _patch_store("history", side_effect=error), pytest.raises(HTTPException) as raised:
        await read_history(point_id="p-1", user=_user())

    assert raised.value.status_code == status_code


# ---- POST /v2/tag-changes/{change_id}/undo, /restore ----

async def test_undo_marks_the_change_and_returns_it():
    undone_at = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)

    with _patch_store("set_undone", return_value=(_change(undone_at=undone_at, undone_by="user-1"), "status")) as store:
        result = await undo_change(change_id=1, user=_user())

    store.assert_awaited_once_with(1, "user-1", True)
    assert (result.id, result.key, result.undone_at, result.undone_by) == (1, "status", undone_at, "user-1")



@pytest.mark.parametrize("error, status_code", [
    (UnknownTagChange(9), 404),
    (NotAuthorized(), 403),
    (StoreUnavailable(), 503),
])
async def test_undo_maps_store_errors_to_http(error, status_code):
    with _patch_store("set_undone", side_effect=error), pytest.raises(HTTPException) as raised:
        await undo_change(change_id=9, user=_user())

    assert raised.value.status_code == status_code
