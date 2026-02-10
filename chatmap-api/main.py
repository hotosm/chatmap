import os
import httpx
import logging
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Request, APIRouter
from fastapi.responses import StreamingResponse, FileResponse
from typing import Dict
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import Point, FeatureCollection, init_db, get_db_session, get_or_create_map, SharePermission, Map
from sqlalchemy.orm import Session
from stream import stream_listener
from settings import DEBUG, API_VERSION, MEDIA_FOLDER, SERVER_URL, CORS_ORIGINS
from sqlalchemy import func
from hotosm_auth_fastapi import setup_auth, CurrentUser

# Logs
logging.basicConfig(
    format='[API] %(levelname)s: %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(debug=DEBUG)
prefix = f"v{API_VERSION}"
api_router = APIRouter(prefix=f"/{prefix}")

# Setup Hanko auth (loads config from .env: HANKO_API_URL)
setup_auth(app)

# DB
init_db()

# Scheduler
scheduler = AsyncIOScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get QR code
@api_router.get("/qr", response_class=StreamingResponse)
async def qr(user: CurrentUser):
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{SERVER_URL}/start-qr?session={user.id}')
        if response.status_code != 200:
            logger.warning(f'Failed to get QR code: {user.id}')
            raise HTTPException(status_code=502, detail="Failed to get QR code")

        if "image" not in response.headers.get("Content-Type", ""):
            raise HTTPException(status_code=400, detail="URL did not return an image")

        return StreamingResponse(BytesIO(response.content), media_type="image/png")

# Get Status
@api_router.get("/status")
async def status(
    user: CurrentUser
) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        print(user.id)
        response = await client.get(f'{SERVER_URL}/status?session={user.id}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to get session")
        status_response = response.json()
        return {'status': status_response['status']}

# Logout
@api_router.get("/logout")
async def logout(user: CurrentUser) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{SERVER_URL}/logout?session={user.id}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to logout")
        return {'status': "logged out"}

# Get public map
@api_router.get("/map/{map_id}", response_model=FeatureCollection, status_code=200)
async def get_public_chatmap(
    map_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
):
    map_obj: Map = db.get(Map, map_id)
    if map_obj and map_obj.sharing == SharePermission.PUBLIC:
        points = (
            db.query(
                Point.id,
                Point.message,
                func.ST_Y(Point.geom).label("lat"),
                func.ST_X(Point.geom).label("lon"),
                Point.username,
                Point.time,
                Point.file,
            )
            .filter(Point.map_id == map_id)
            .all()
        )

        return {
            "id": map_id,
            "sharing": map_obj.sharing.value,
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "time": point.time,
                        "username_id": point.username,
                        "message": point.message,
                        "file": point.file,
                        "id": point.id,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [point.lon, point.lat],
                    }
                }
                for point in points
            ]
        }
    else:
        # Map is not public – reject the request
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: the requested map is not publicly shared."
        )

# Get map points for user
@api_router.get("/map", response_model=FeatureCollection)
async def get_chatmap(
    request: Request,
    user: CurrentUser,
    db: Session = Depends(get_db_session),
):
    map_id = get_or_create_map(db, user.id)
    map_obj: Map = db.get(Map, map_id)
    points = (
        db.query(
            Point.id,
            Point.message,
            func.ST_Y(Point.geom).label("lat"),
            func.ST_X(Point.geom).label("lon"),
            Point.username,
            Point.time,
            Point.file,
        )
        .filter(Point.map_id == map_id)
        .all()
    )

    return {
        "id": map_id,
        "sharing": map_obj.sharing.value,
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "time": point.time,
                    "username_id": point.username,
                    "message": point.message,
                    "file": point.file,
                    "id": point.id,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [point.lon, point.lat],
                }
            }
            for point in points
        ]
    }

# Update map sharing permissions
@api_router.put("/map/share")
async def status(
    user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    map_id = get_or_create_map(db, user.id)
    map_obj: Map = db.get(Map, map_id)
    sharing = (
        SharePermission.PUBLIC
        if map_obj.sharing == SharePermission.PRIVATE
        else SharePermission.PRIVATE
    )
    map_obj.sharing = sharing
    db.commit()
    return {"map_id": map_id, "sharing": map_obj.sharing.value}

# Get media file (image/jpeg)
@api_router.get("/media")
async def media(filename: str) -> Dict[str, str]:
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

# Get Status
@api_router.get("/version")
async def version():
    return {'version': "0.0.5"}

# Protected endpoint example (requires Hanko auth)
@api_router.get("/me")
async def me(user: CurrentUser):
    """Get current authenticated user info. Requires valid Hanko session."""
    return {
        'user_id': user.id,
        'email': user.email,
        'username': user.username,
    }

# API Router
app.include_router(api_router)

# On API startup
@api_router.on_event("startup")
async def startup_event():
    print(f"Starting ...")
    global scheduler
    if not os.path.exists("media"):
        os.mkdir("media")
    asyncio.create_task(stream_listener())

# On API shutdown
@api_router.on_event("shutdown")
async def shutdown_event():
    print(f"Shutting down ...")
