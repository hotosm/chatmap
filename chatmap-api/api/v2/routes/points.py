from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from api.v2.credentials import RequestCredentials, require_contributor_secret, require_credential
from api.v2.schemas.media import MediaResponse
from api.v2.schemas.point import CreatePointRequest, CreatePointResponse, HistoryPointResponse, HistoryResponse
from results.error import InvalidCursor, MapNotFound, NotAuthorized, StoreUnavailable
from settings import API_URL
from store.contributors.authorization import Owner
from store.contributors.model import Contributor
from store.contributors.store import ContributorStore
from store.maps.store import MapStore
from store.points.store import HistoryMedia, HistoryPoint, PointStore

router = APIRouter()


async def point_author(point: CreatePointRequest, credentials: RequestCredentials) -> Owner | Contributor:
    try:
        return await MapStore.role_of(point.map_id, credentials)
    except MapNotFound:
        raise HTTPException(status_code=404, detail="Map not found.")
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Point storage unavailable.")


PointAuthor = Annotated[Owner | Contributor, Depends(point_author)]


async def history_contributor(map_id: str, credentials: RequestCredentials) -> Contributor:
    try:
        return await ContributorStore.active_in(map_id, credentials)
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Point storage unavailable.")


HistoryContributor = Annotated[Contributor, Depends(history_contributor)]


@router.post("/points", status_code=201, dependencies=[Depends(require_credential)])
async def create_point(
        point: CreatePointRequest,
        response: Response,
        author: PointAuthor,
) -> CreatePointResponse:
    try:
        creation = await PointStore.create_point(
            map_id=point.map_id,
            author=author,
            latitude=point.latitude,
            longitude=point.longitude,
            time=point.time,
            message=point.message,
        )
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Point storage unavailable.")

    response.status_code = 201 if creation.created else 200

    return CreatePointResponse(id=creation.id)


def _media_response(media: HistoryMedia | None) -> MediaResponse | None:
    if media is None:
        return None

    return MediaResponse(
        id=media.id,
        url=f"{API_URL}/v2/media/{media.id}",
        content_type=media.content_type,
        size=media.size,
        captured_at=media.captured_at,
    )


def _point_response(point: HistoryPoint) -> HistoryPointResponse:
    return HistoryPointResponse(
        id=point.id,
        time=point.time,
        latitude=point.latitude,
        longitude=point.longitude,
        message=point.message,
        media=_media_response(point.media),
    )


@router.get("/maps/{map_id}/points", dependencies=[Depends(require_contributor_secret)])
async def list_points(
        map_id: str,
        contributor: HistoryContributor,
        cursor: str | None = None,
) -> HistoryResponse:
    try:
        page = await PointStore.contributor_points(map_id, contributor, cursor)
    except InvalidCursor:
        raise HTTPException(status_code=422, detail="Invalid cursor.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Point storage unavailable.")

    return HistoryResponse(points=[_point_response(point) for point in page.points], next=page.next)
