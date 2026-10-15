from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import AwareDatetime
from starlette.background import BackgroundTask

from api.v2.credentials import RequestCredentials, require_credential
from api.v2.schemas.media import MediaResponse
from results.error import NotAuthorized, PointAlreadyHasMedia, StoreUnavailable, UnsupportedMediaType
from settings import API_URL
from store.contributors.authorization import Owner
from store.contributors.model import Contributor
from store.media.store import MediaStore

router = APIRouter()


async def media_uploader(point_id: str, credentials: RequestCredentials) -> Owner | Contributor:
    try:
        return await MediaStore.uploader_of(point_id, credentials)
    except NotAuthorized:
        raise HTTPException(status_code=403, detail="Not authorized.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Media storage unavailable.")


MediaUploader = Annotated[Owner | Contributor, Depends(media_uploader)]


@router.post("/points/{point_id}/media", status_code=201, dependencies=[Depends(require_credential)])
async def add_media(
        point_id: str,
        file: UploadFile,
        captured_at: Annotated[AwareDatetime, Form()],
        uploader: MediaUploader,
) -> MediaResponse:
    filename = file.filename or ""
    data = await file.read()

    try:
        media = await MediaStore.add_media(point_id, uploader, filename, data, captured_at)
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
        captured_at=media.captured_at.replace(tzinfo=timezone.utc) if media.captured_at else None,
    )


@router.get("/media/{media_id}", response_class=StreamingResponse)
async def read_media(
        media_id: str,
        credentials: RequestCredentials,
):
    try:
        result = await MediaStore.read_media(media_id, credentials)
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
