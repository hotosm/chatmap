"""
This FastAPI application serves as the backend for the system that ingests
real-time messages from a Redis stream and stores them in a database.
These messages are then used to generate a GeoJSON-based map showing locations
and related content.
"""

import os
import httpx
import logging
import asyncio
from pathlib import Path
from uuid import uuid4
from collections import defaultdict
from aiobotocore.session import get_session
from typing import Annotated
from fastapi import (
    FastAPI, HTTPException, Depends, Request, APIRouter, File, UploadFile,
)
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from typing import Dict
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import Point, get_db_session, get_or_create_live_map, SharePermission, Map
from schemas import (
    FeatureCollection, SaveMapFeatureCollection, SaveMapResult, UpdateMap,
    SaveMediaResponse, PointTags, AddPointsFeatureCollection, AddPointsResult,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from stream import stream_listener
from settings import (
    DEBUG, API_VERSION, MEDIA_FOLDER, SERVER_URL, CORS_ORIGINS,
    S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_NAME, S3_ENDPOINT_URL, API_URL,
)
from sqlalchemy import func, select
from geoalchemy2.shape import to_shape
from hotosm_auth_fastapi import setup_auth, CurrentUser, CurrentUserOptional

# Logs
logging.basicConfig(
    format='[API] %(levelname)s: %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# FastAPI App Initialization
app = FastAPI(debug=DEBUG)
prefix = f"v{API_VERSION}"
api_router = APIRouter(prefix=f"/{prefix}")

# Setup Hanko auth
setup_auth(app)

# Scheduler for background tasks (e.g., get messages and update maps)
scheduler = AsyncIOScheduler()

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_TYPE = defaultdict(lambda: "application/octet-stream", {
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".opus": "audio/opus",
})

# QR Code Endpoint
@api_router.get("/qr", response_class=StreamingResponse)
async def qr(user: CurrentUser):
    """
    Retrieve a QR code image for linking devices

    Args:
        user (CurrentUser): Authenticated user.

    Returns:
        StreamingResponse: Streamed image response.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{SERVER_URL}/start-qr?session={user.id}')
        if response.status_code != 200:
            logger.warning(f'Failed to get QR code: {user.id}')
            raise HTTPException(status_code=502, detail="Failed to get QR code")

        if "image" not in response.headers.get("Content-Type", ""):
            raise HTTPException(status_code=400, detail="URL did not return an image")

        return StreamingResponse(BytesIO(response.content), media_type="image/png")

# Session Status Endpoint
@api_router.get("/status")
async def status(
    user: CurrentUser,
) -> Dict[str, str]:
    """
    Get the current session status of the linked device.

    Args:
        user (CurrentUser): Authenticated user.

    Returns:
        Dict[str, str]: Status of the session.
    """
    async with httpx.AsyncClient() as client:
        print(user.id)
        response = await client.get(f'{SERVER_URL}/status?session={user.id}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to get session")
        status_response = response.json()
        return {'status': status_response['status']}

# Logout Endpoint
@api_router.get("/logout")
async def logout(user: CurrentUser) -> Dict[str, str]:
    """
    Log out the linked device.

    Args:
        user (CurrentUser): Authenticated user.

    Returns:
        Dict[str, str]: Confirmation of logout.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{SERVER_URL}/logout?session={user.id}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to logout")
        return {'status': "logged out"}


# List user maps endpoint
@api_router.get("/user/{user_id}/map")
async def list_user_maps(
    user_id: str,
    db: Session = Depends(get_db_session),
):
    return list_maps_result(user_id, db)

# List maps endpoint
@api_router.get("/map")
async def list_maps(
    user: CurrentUserOptional,
    db: Session = Depends(get_db_session),
):
    return list_maps_result(user.id if user else None, db)

# Function for listing maps
def list_maps_result(
    userId: str,
    db: Session,
):
    """
    List maps

    Args:
        user (CurrentUserOptional): Authenticated user (optional)
        db (Session): Database session.

    Returns:
        List[Dict[str, str]]: List of maps
    """
    subq = (
        select(func.count(Point.id).label("count"), Point.map_id)
            .group_by(Point.map_id)
            .subquery()
    )
    if userId:
        map_filter = Map.owner_id == userId
    else:
        map_filter = Map.sharing == SharePermission.PUBLIC
    maps = db.execute(
        select(Map, subq.c.count)
            .join_from(Map, subq)
            .where(map_filter)
            .order_by(Map.created_at.desc())
    )

    results = []
    for map_obj, count in maps:
        centroid = map_obj.centroid
        if centroid:
            geom = to_shape(centroid)
            centroid_coords = [geom.y, geom.x]
        else:
            centroid_coords = None

        results.append({
            "id": map_obj.id,
            "name": map_obj.name,
            "updated_at": map_obj.updated_at,
            "sharing": map_obj.sharing,
            "count": count,
            "centroid": centroid_coords
    })
    return results


@api_router.post("/map/media")
async def save_media(
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
) -> SaveMediaResponse:
    session = get_session()

    s3_client_kwargs = {
        'endpoint_url': S3_ENDPOINT_URL,
    }
    if S3_ACCESS_KEY:
        s3_client_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
    if S3_SECRET_KEY:
        s3_client_kwargs['aws_secret_access_key'] = S3_SECRET_KEY

    async with session.create_client(
        's3', **s3_client_kwargs) as client:
        ext = Path(file.filename).suffix
        filename = str(uuid4()) + ext
        resp = await client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=filename,
            Body=await file.read(),
        )

    return SaveMediaResponse(uri=f"{API_URL}/v1/media/{filename}")


@api_router.post("/map")
async def create_map(
    map_data: SaveMapFeatureCollection,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> SaveMapResult:
    with db.begin():
        new_map = Map(owner_id=user.id, name=map_data.name, description=map_data.description)
        db.add(new_map)
        db.flush()

        db.add_all([Point(
            geom=f"POINT ({feature.geometry.coordinates[0]} {feature.geometry.coordinates[1]})",
            message=feature.properties.message,
            username=feature.properties.username,
            time=feature.properties.time,
            file=feature.properties.file,
            tags=feature.properties.tags,
            removed=feature.properties.removed or False,
            map_id=new_map.id,
        ) for feature in map_data.features])

    return SaveMapResult(id=new_map.id, name=new_map.name)


@api_router.post("/map/{map_id}/points/")
async def add_points_to_map(
    map_id: str,
    map_data: AddPointsFeatureCollection,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
):
    """
    Add points to an existing map

    Args:
        map_id (str): Unique identifier of the map.
        map_data (dict): FeatureCollection with the new points
        user: Authenticated user
        db (Session): Database session.

    Returns:
        Dict[str, str]: Updated map ID
    """
    map = db.get(Map, map_id)

    if map is None or map.owner_id != user.id:
        raise HTTPException(
            status_code=404,
            detail="Map not found",
        )

    db.add_all([Point(
        geom=f"POINT ({feature.geometry.coordinates[0]} {feature.geometry.coordinates[1]})",
        message=feature.properties.message,
        username=feature.properties.username,
        time=feature.properties.time,
        file=feature.properties.file,
        tags=feature.properties.tags,
        removed=feature.properties.removed or False,
        map_id=map.id,
    ) for feature in map_data.features])
    db.commit()

    return AddPointsResult(id=map_id, count=len(map_data.features))


@api_router.delete("/map/{map_id}")
async def delete_map(
    map_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
):
    map = db.get(Map, map_id)

    if map is None or map.owner_id != user.id:
        raise HTTPException(
            status_code=404,
            detail="Map not found",
        )

    # Delete media associated with the map
    session = get_session()

    s3_client_kwargs = {
        'endpoint_url': S3_ENDPOINT_URL,
    }
    if S3_ACCESS_KEY:
        s3_client_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
    if S3_SECRET_KEY:
        s3_client_kwargs['aws_secret_access_key'] = S3_SECRET_KEY

    async with session.create_client(
        's3', **s3_client_kwargs) as client:
        for point in map.points:
            if not point.file:
                continue

            filename = point.file.rsplit("/", 1)

            resp = await client.delete_object(
                Bucket=S3_BUCKET_NAME,
                Key=filename[-1],
            )

    db.delete(map)
    db.commit()

    return

@api_router.get("/media_player/{media_url}", response_class=HTMLResponse)
async def get_video_player(
    media_url: str,
    request: Request,
):
    """
    Retrieve HTML for a video player

    Args:
        file (str): Media file URL
        request (Request): FastAPI request object.

    Returns:
        HTML for a video player
    """
    html_response = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Video</title></head>
    <body>
    """

    if media_url.endswith("mp4"):
        html_response += f"""
        <video width="490" height="350" style="background-color: #111; border-radius: 4px" controls>
        <source src="{API_URL}/v{API_VERSION}/media?filename={media_url}" type="video/mp4">
        Your browser does not support the video tag.
        </video>
        """
    elif (media_url.endswith("ogg") or
        media_url.endswith("opus") or
        media_url.endswith("mp3") or
        media_url.endswith("m4a") or
        media_url.endswith("wav")
    ):
        file_type = media_url[-4:] if media_url.endswith("opus") else media_url[-3:]
        html_response += f"""
        <audio width="490" height="68" style="background-color: #111; border-radius: 4px" controls>
        <source src="{API_URL}/v{API_VERSION}/media?filename={media_url}" type="audio/{file_type}">
        Your browser does not support the audio tag.
        </audio>
        """

    html_response += """
    </body>
    </html>
    """
    return html_response

# Retrieve HTML for embedded media (image/video/audio)
def html_for_embedded_media(file):
    if file:
      filename = file.split("=")[1]
      file_url = f"{API_URL}/v{API_VERSION}/media_player/{filename}"
      if file.endswith("jpg") or file.endswith("jpeg"):
        return f"<img src=\"{file}\" />"
      elif file.endswith("mp4"):
        return f"<iframe width=\"495\" height=\"365\" src=\"{file_url}\" title=\"Video player\" scrolling=\"no\" frameborder=\"0\"></iframe>"
      elif (file.endswith("ogg") or
        file.endswith("opus") or
        file.endswith("mp3") or
        file.endswith("m4a") or
        file.endswith("wav")
      ):
        return f"<iframe width=\"495\" height=\"65\" src=\"{file_url}\" title=\"Audio player\" scrolling=\"no\" frameborder=\"0\"></iframe>"
    else:
      return "Location only"

def map_response(db, map_obj, owner):

    # Filter points by map id
    base_filter = Point.map_id == map_obj.id
    
    # If user is not owner of the map, exclude removed points
    if not owner:
        base_filter = base_filter & (Point.removed == False)
        
    points = (
        db.query(
            Point.id,
            Point.message,
            func.ST_Y(Point.geom).label("lat"),
            func.ST_X(Point.geom).label("lon"),
            Point.username,
            Point.time,
            Point.file,
            Point.removed,
            Point.tags,
        )
        .filter(base_filter)
        .all()
    )

    return {
        "id": map_obj.id,
        "sharing": map_obj.sharing.value,
        "name": map_obj.name,
        "description": map_obj.description,
        "owner": owner, 
        "is_live": map_obj.is_live,
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "time": point.time,
                    "message": point.message or "",
                    "file": point.file,
                    "file_embedded": html_for_embedded_media(point.file),
                    "tags": point.tags or "",
                    "id": point.id,
                    "removed": point.removed,
                    "tags": point.tags or ""
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.lon, point.lat],
                }
            }
            for point in points
        ]
    }

@api_router.get("/map/new", response_model=FeatureCollection)
async def get_map(
    request: Request,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
):
    """
    Retrieve private map data (GeoJSON) for the authenticated user.

    Args:
        request (Request): FastAPI request object.
        user (CurrentUser): Authenticated user.
        db (Session): Database session.

    Returns:
        FeatureCollection: GeoJSON FeatureCollection of points.
    """
    map_id = get_or_create_live_map(db, user.id)
    map_obj: Map = db.get(Map, map_id)

    return map_response(db, map_obj, True)


@api_router.get("/map/{map_id}", response_model=FeatureCollection, status_code=200)
async def get_public_map(
    map_id: str,
    request: Request,
    user: CurrentUserOptional,
    db: Session = Depends(get_db_session),
):
    """
    Retrieve public map data (GeoJSON) for a given map ID.

    Args:
        map_id (str): Unique identifier of the map.
        request (Request): FastAPI request object.
        db (Session): Database session.

    Returns:
        FeatureCollection: GeoJSON FeatureCollection of points.
    """
    map_obj: Map = db.get(Map, map_id)

    owner = (user and map_obj.owner_id == user.id) or False
    if map_obj and (map_obj.sharing == SharePermission.PUBLIC or owner):
        return map_response(db, map_obj, owner)
    else:
        # Map is not public – reject the request
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: the requested map is not publicly shared."
        )


# Toggle Map Sharing Permission
@api_router.put("/map/{map_id}/share/")
async def status(
    map_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """
    Toggle sharing permission of the user's map between private and public.

    Args:
        map_id (str): Unique identifier of the map.
        user (CurrentUser): Authenticated user.
        db (Session): Database session.

    Returns:
        Dict[str, str]: Updated map ID and sharing status.
    """
    map_obj: Map = db.get(Map, map_id)
    if map_obj and user and map_obj.owner_id == user.id:
        sharing = (
            SharePermission.PUBLIC
            if map_obj.sharing == SharePermission.PRIVATE
            else SharePermission.PRIVATE
        )
        map_obj.sharing = sharing
        db.commit()
        return {"map_id": map_id, "sharing": map_obj.sharing.value}
    else:
        # User is not owner of the map
        raise HTTPException(
            status_code=401,
            detail="Unauthorized."
        )

# Update map
@api_router.put("/map/{map_id}")
async def status(
    map_id: str,
    map_data: UpdateMap,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """
    Edit user's map title, description

    Args:
        map_id (str): Unique identifier of the map.
        title (str): Map's title
        description (str): Map's description
        db (Session): Database session.

    Returns:
        Dict[str, str]: Updated map ID, title and descrition.
    """
    map_obj: Map = db.get(Map, map_id)
    if map_obj and user and map_obj.owner_id == user.id:
        map_obj.name = map_data.name
        map_obj.description = map_data.description
        db.commit()
        return {"map_id": map_id, "name": map_obj.name, "description": map_obj.description}
    else:
        # User is not owner of the map
        raise HTTPException(
            status_code=401,
            detail="Unauthorized."
        )


@api_router.put("/point/{point_id}/remove/")
async def remove_point(
    point_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
):
    point_obj: Point = db.get(Point, point_id)
    if point_obj:
        map_obj = point_obj.map
        if map_obj.owner_id == user.id:
            point_obj.removed = not point_obj.removed
            db.commit()
            return {"removed": point_obj.removed}
        else:
            # User is not owner of the map
            raise HTTPException(
                status_code=401,
                detail="Unauthorized."
            )
    raise HTTPException(
        status_code=404,
        detail="Point not found",
    )

@api_router.put("/point/{point_id}/tags/")
async def update_point_tags(
    point_id: str,
    tags: PointTags,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
):
    print(tags)
    point_obj: Point = db.get(Point, point_id)
    if point_obj:
        map_obj = point_obj.map
        if map_obj.owner_id == user.id:
            point_obj.tags = tags.tags
            db.commit()
            return {"tags": point_obj.tags}
        else:
            # User is not owner of the map
            raise HTTPException(
                status_code=401,
                detail="Unauthorized."
            )
    raise HTTPException(
        status_code=404,
        detail="Point not found",
    )

@api_router.get("/media/{filename}", response_class=StreamingResponse)
async def get_media(
    filename: str,
    user: CurrentUserOptional,
    db: Session = Depends(get_db_session),
):
    # first check if file is registered and accesible to the current user
    try:
        point = db.query(Point).filter(Point.file.like(f"%{filename}")).one()
        map_obj = point.map

        if map_obj.sharing != SharePermission.PUBLIC and (not user or map_obj.owner_id != user.id):
            raise HTTPException(
                status_code=404,
                detail="Media not found",
            )
    except NoResultFound:
        raise HTTPException(
            status_code=404,
            detail="Media not found",
        )

    session = get_session()

    s3_client_kwargs = {
        'endpoint_url': S3_ENDPOINT_URL,
    }
    if S3_ACCESS_KEY:
        s3_client_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
    if S3_SECRET_KEY:
        s3_client_kwargs['aws_secret_access_key'] = S3_SECRET_KEY

    async with session.create_client(
        's3', **s3_client_kwargs) as client:
        try:
            resp = await client.get_object(Bucket=S3_BUCKET_NAME, Key=filename)

            ext = Path(filename).suffix

            async with resp['Body'] as stream:
                return StreamingResponse(BytesIO(await stream.read()), media_type=MEDIA_TYPE[ext])
        except client.exceptions.NoSuchKey:
            raise HTTPException(
                status_code=404,
                detail="Media not found",
            )

# Media File Endpoint
@api_router.get("/media")
async def media(filename: str) -> Dict[str, str]:
    """
    Serve media files (images, videos, audio)

    Args:
        filename (str): Name of the media file.

    Returns:
        FileResponse or error message.
    """
    file_path = os.path.join(MEDIA_FOLDER, filename)
    if not os.path.isfile(file_path):
        return {"error": "File not found"}
    if filename[-3:] == "jpg":
        return FileResponse(path=file_path, media_type="image/jpeg")
    elif filename[-3:] == "mp4":
        return FileResponse(path=file_path, media_type="video/mp4")
    elif filename[-4:] == "opus":
        return FileResponse(path=file_path, media_type="audio/opus")
    return {"error": "Format unknown"}

# Protected User Info Endpoint
@api_router.get("/me")
async def me(user: CurrentUser):
    """
    Return information about the authenticated user.

    Args:
        user (CurrentUser): Authenticated user.

    Returns:
        Dict[str, str]: User info including ID, email, and username.
    """
    return {
        'user_id': user.id,
        'email': user.email,
        'username': user.username,
    }

# Include API Router
app.include_router(api_router)

# On API startup
@api_router.on_event("startup")
async def startup_event():
    """
    Perform actions when the API starts up.
    Ensures media directory exists and starts the Redis stream listener.
    """
    print(f"Starting ...")
    global scheduler
    if not os.path.exists("media"):
        os.mkdir("media")
    asyncio.create_task(stream_listener())

# On API shutdown
@api_router.on_event("shutdown")
async def shutdown_event():
    """
    Perform actions when the API shuts down.
    """
    print(f"Shutting down ...")
