from fastapi import APIRouter, HTTPException
from hotosm_auth_fastapi import CurrentUser, CurrentUserOptional

from api.v2.schemas.statuses import (
    MapStatusItem, MapStatuses, MapStatusesResponse, PointStatus, PointStatusItem, PointStatusResponse,
)
from results.error import NotAuthorized, StoreUnavailable, UnknownStatus
from store.map_statuses_store import MapStatusesStore

router = APIRouter()


def _status_item(row) -> MapStatusItem:
    return MapStatusItem(id=row.id, name=row.name, description=row.description or "", color=row.color)


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
            PointStatusItem(id=point.id, status=point.status_id, status_updated_at=point.status_updated_at)
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
            map_id, user.id, [status.model_dump() for status in statuses.statuses],
        )
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
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
        status_id, updated_at = await MapStatusesStore.set_point_status(point_id, user.id, point_status.status)
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except UnknownStatus:
        raise HTTPException(status_code=404, detail="Status not found.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Statuses storage unavailable.")

    return PointStatusResponse(status=status_id, status_updated_at=updated_at)
