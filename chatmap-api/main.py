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


# FastAPI App Initialization
app = FastAPI(debug=DEBUG)
prefix = f"v{API_VERSION}"
api_router = APIRouter(prefix=f"/{prefix}")

# Setup Hanko auth
setup_auth(app)

# Initialize database connection and tables
init_db()

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
    user: CurrentUser
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

# Public Map Data Endpoint
@api_router.get("/map/{map_id}", response_model=FeatureCollection, status_code=200)
async def get_public_chatmap(
    map_id: str,
    request: Request,
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

# User's Private Map Data Endpoint
@api_router.get("/map", response_model=FeatureCollection)
async def get_chatmap(
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

# Toggle Map Sharing Permission
@api_router.put("/map/share")
async def status(
    user: CurrentUser,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """
    Toggle sharing permission of the user's map between private and public.
    
    Args:
        user (CurrentUser): Authenticated user.
        db (Session): Database session.
        
    Returns:
        Dict[str, str]: Updated map ID and sharing status.
    """
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
