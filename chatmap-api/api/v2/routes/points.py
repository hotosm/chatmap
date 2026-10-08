from fastapi import APIRouter, HTTPException, Response
from hotosm_auth_fastapi import CurrentUser

from api.v2.schemas.point import CreatePointRequest, CreatePointResponse
from results.error import MapNotFound, PointIdAlreadyTaken, StoreUnavailable
from store.point_store import PointStore

router = APIRouter()


@router.post("/points", status_code=201)
async def create_point(
        point: CreatePointRequest,
        response: Response,
        user: CurrentUser,
) -> CreatePointResponse:
    point_id = str(point.id)

    try:
        created = await PointStore.create_point(
            point_id=point_id,
            map_id=point.map_id,
            user_id=user.id,
            username=user.username,
            latitude=point.latitude,
            longitude=point.longitude,
            time=point.time,
            message=point.message,
        )
    except MapNotFound:
        raise HTTPException(status_code=404, detail="Map not found.")
    except PointIdAlreadyTaken:
        raise HTTPException(status_code=409, detail="Point id already taken.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Point storage unavailable.")

    response.status_code = 201 if created else 200

    return CreatePointResponse(id=point_id)
