from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from hotosm_auth_fastapi import CurrentUser, CurrentUserOptional
from starlette.background import BackgroundTask

from api.v2.schemas.media import MediaResponse
from results.error import (
    NotAuthorized, PointAlreadyHasMedia, StoreUnavailable, UnsupportedMediaType,
)
from settings import API_URL
from store.media_store import MediaStore

router = APIRouter()


@router.post("/points/{point_id}/media", status_code=201)
async def add_media(
        point_id: str,
        file: UploadFile,
        user: CurrentUser,
) -> MediaResponse:
    try:
        media = await MediaStore.add_media(point_id, user.id, file.filename or "", await file.read())
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except UnsupportedMediaType as error:
        raise HTTPException(status_code=415, detail=f"Unsupported media type '{error.extension}'.")
    except PointAlreadyHasMedia:
        raise HTTPException(status_code=409, detail="Point already has media.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Media storage unavailable.")

    return MediaResponse(
        id=media.id,
        url=f"{API_URL}/v2/media/{media.id}",
        content_type=media.content_type,
        size=media.size,
    )


@router.get("/media/{media_id}", response_class=StreamingResponse)
async def read_media(
        media_id: str,
        user: CurrentUserOptional,
):
    try:
        result = await MediaStore.read_media(media_id, user.id if user else None)
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Media storage unavailable.")

    if result is None:
        raise HTTPException(status_code=404, detail="Media not found.")

    media, body = result
    return StreamingResponse(
        body.iter_chunks(chunk_size=64 * 1024),
        media_type=media.content_type,
        headers={"Content-Length": str(media.size)},
        background=BackgroundTask(body.close),
    )
