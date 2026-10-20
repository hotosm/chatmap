from fastapi import APIRouter, HTTPException
from hotosm_auth_fastapi import CurrentUser, CurrentUserOptional

from api.v2.errors import call_store
from api.v2.schemas.tags import (
    PointTagItem,
    PointTagsResponse,
    TagChangeItem,
    TagChangeRequest,
    TagHistoryResponse,
)
from store.point_tags_store import PointTagsStore

router = APIRouter()


def _tag_item(tag) -> PointTagItem:
    return PointTagItem(
        point_id=tag.point_id,
        key_id=tag.key_id,
        value_id=tag.value_id,
        value=tag.value,
        since=tag.since,
        confirmed_at=tag.confirmed_at,
    )


def _change_item(change, key: str) -> TagChangeItem:
    return TagChangeItem(
        id=change.id,
        key=key,
        action=change.action,
        value_id=change.value_id,
        value=change.value,
        happened_at=change.happened_at,
        recorded_at=change.recorded_at,
        source=change.source,
        user_id=change.user_id,
        undone_at=change.undone_at,
        undone_by=change.undone_by,
    )


@router.get("/maps/{map_id}/tags")
async def read_tags(map_id: str, user: CurrentUserOptional) -> PointTagsResponse:
    tags = await call_store(PointTagsStore.read_tags(map_id, user.id if user else None))
    if tags is None:
        raise HTTPException(status_code=404, detail="Map not found.")
    return PointTagsResponse(tags=[_tag_item(tag) for tag in tags])


@router.put("/points/{point_id}/tags/{key_id}")
async def set_point_tag(point_id: str, key_id: str, change: TagChangeRequest, user: CurrentUser) -> PointTagsResponse:
    tags = await call_store(PointTagsStore.set_point_tag(
        point_id, key_id, user.id, change.action,
        value_id=change.value_id, value=change.value, happened_at=change.happened_at,
    ))
    return PointTagsResponse(tags=[_tag_item(tag) for tag in tags])


@router.get("/points/{point_id}/history")
async def read_history(point_id: str, user: CurrentUser) -> TagHistoryResponse:
    rows = await call_store(PointTagsStore.history(point_id, user.id))
    return TagHistoryResponse(changes=[_change_item(change, key) for change, key in rows])


@router.post("/tag-changes/{change_id}/undo")
async def undo_change(change_id: int, user: CurrentUser) -> TagChangeItem:
    change, key = await call_store(PointTagsStore.set_undone(change_id, user.id, True))
    return _change_item(change, key)


@router.post("/tag-changes/{change_id}/restore")
async def restore_change(change_id: int, user: CurrentUser) -> TagChangeItem:
    change, key = await call_store(PointTagsStore.set_undone(change_id, user.id, False))
    return _change_item(change, key)
