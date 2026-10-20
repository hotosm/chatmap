from fastapi import APIRouter, HTTPException
from hotosm_auth_fastapi import CurrentUser

from api.v2.schemas.tag_changes import TagChangeItem, TagHistoryResponse
from results.error import NotAuthorized, StoreUnavailable, UnknownTagChange
from store.point_tags_store import PointTagsStore

router = APIRouter()


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


@router.get("/points/{point_id}/history")
async def read_history(
        point_id: str,
        user: CurrentUser,
) -> TagHistoryResponse:
    try:
        rows = await PointTagsStore.history(point_id, user.id)
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Tags storage unavailable.")

    return TagHistoryResponse(changes=[_change_item(change, key) for change, key in rows])


async def _set_undone(change_id: int, user_id: str, undone: bool) -> TagChangeItem:
    try:
        change, key = await PointTagsStore.set_undone(change_id, user_id, undone)
    except UnknownTagChange:
        raise HTTPException(status_code=404, detail="Change not found.")
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Tags storage unavailable.")

    return _change_item(change, key)


@router.post("/tag-changes/{change_id}/undo")
async def undo_change(change_id: int, user: CurrentUser) -> TagChangeItem:
    return await _set_undone(change_id, user.id, True)


@router.post("/tag-changes/{change_id}/restore")
async def restore_change(change_id: int, user: CurrentUser) -> TagChangeItem:
    return await _set_undone(change_id, user.id, False)
