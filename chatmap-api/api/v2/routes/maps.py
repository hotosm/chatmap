from fastapi import APIRouter, HTTPException
from hotosm_auth_fastapi import CurrentUserOptional

from api.v2.schemas.maps import MapResponse
from api.v2.schemas.statuses import MapStatusItem
from results.error import StoreUnavailable
from store.map_statuses_store import MapStatusesStore
from store.maps_store import MapsStore
from store.survey_responses_store import SurveyResponsesStore

router = APIRouter()


@router.get("/maps/{map_id}")
async def read_map(
        map_id: str,
        user: CurrentUserOptional,
) -> MapResponse:
    try:
        result = await MapsStore.read_map(map_id, user.id if user else None)

        if result is None:
            raise HTTPException(status_code=404, detail="Map not found.")

        map_obj, owner, points = result
        statuses = await MapStatusesStore.statuses_for(map_id)
        survey_by_point = await SurveyResponsesStore.responses_for_points(
            map_id=map_id, point_ids=[point.id for point in points],
        )
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Map storage unavailable.")

    # A point only shows a status that belongs to its own map
    status_ids = {status.id for status in statuses}

    return MapResponse(
        id=map_obj.id,
        name=map_obj.name,
        description=map_obj.description,
        sharing=map_obj.sharing.value,
        owner=owner,
        is_live=map_obj.is_live,
        type="FeatureCollection",
        statuses=[
            MapStatusItem(id=status.id, name=status.name, description=status.description or "", color=status.color)
            for status in statuses
        ],
        features=[
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [point.lon, point.lat]},
                "properties": {
                    "id": point.id,
                    "time": point.time,
                    "message": point.message or "",
                    "file": point.file,
                    "tags": point.tags or "",
                    "removed": point.removed,
                    "status": point.status_id if point.status_id in status_ids else None,
                    "status_updated_at": point.status_updated_at if point.status_id in status_ids else None,
                    "survey": survey_by_point.get(point.id, []),
                },
            }
            for point in points
        ],
    )
