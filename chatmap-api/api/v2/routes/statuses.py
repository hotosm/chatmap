from fastapi import APIRouter, HTTPException
from hotosm_auth_fastapi import CurrentUser, CurrentUserOptional

from api.v2.schemas.statuses import (
    MapStatuses,
    MapStatusesResponse,
    MapStatusItem,
    PointStatus,
    PointStatusItem,
    PointStatusResponse,
)
from results.error import (
    ArchivedStatus,
    NotAuthorized,
    StatusInUse,
    StoreUnavailable,
    UnknownStatus,
)
from store.map_statuses_store import MapStatusesStore

router = APIRouter()


def _status_item(row) -> MapStatusItem:
    return MapStatusItem(
        id=row.id,
        name=row.value,
        description=row.description or "",
        color=row.color,
        expires_after=int(row.expires_after.total_seconds() // 3600) if row.expires_after else None,
        archived=row.archived_at is not None,
        archived_at=row.archived_at,
    )


def _point_status(tag) -> PointStatusResponse:
    if tag is None:
        return PointStatusResponse(status=None, status_updated_at=None)
    return PointStatusResponse(
        status=tag.value_id, since=tag.since, confirmed_at=tag.confirmed_at, status_updated_at=tag.confirmed_at,
    )


@router.get("/maps/{map_id}/statuses")
async def read_statuses(
        map_id: str,
        user: CurrentUserOptional,
) -> MapStatusesResponse:
    try:
        result = await MapStatusesStore.read_statuses(map_id, user.id if user else None)
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Statuses storage unavailable.")

    if result is None:
        raise HTTPException(status_code=404, detail="Map not found.")

    statuses, points = result
    return MapStatusesResponse(
        statuses=[_status_item(status) for status in statuses],
        points=[
            PointStatusItem(
                id=point.point_id,
                status=point.value_id,
                since=point.since,
                confirmed_at=point.confirmed_at,
                status_updated_at=point.confirmed_at,
            )
            for point in points
        ],
    )


@router.put("/maps/{map_id}/statuses")
async def set_statuses(
        map_id: str,
        statuses: MapStatuses,
        user: CurrentUser,
) -> MapStatuses:
    try:
        rows = await MapStatusesStore.set_statuses(
            map_id, user.id, [status.model_dump(exclude={"archived_at"}) for status in statuses.statuses],
        )
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except StatusInUse:
        raise HTTPException(status_code=409, detail="A status some points have cannot be removed, only archived.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Statuses storage unavailable.")

    return MapStatuses(statuses=[_status_item(row) for row in rows])


@router.put("/points/{point_id}/status")
async def set_point_status(
        point_id: str,
        point_status: PointStatus,
        user: CurrentUser,
) -> PointStatusResponse:
    try:
        tag = await MapStatusesStore.set_point_status(
            point_id, user.id, point_status.status, point_status.happened_at,
        )
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except UnknownStatus:
        raise HTTPException(status_code=404, detail="Status not found.")
    except ArchivedStatus:
        raise HTTPException(status_code=409, detail="Status is archived.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Statuses storage unavailable.")

    return _point_status(tag)
