import os
import httpx
import logging
import uuid
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Request, APIRouter
from fastapi.responses import StreamingResponse, FileResponse
from typing import Dict, List
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import Point, PointOut, init_db, load_session, save_session, remove_session, get_db_session
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from stream import stream_listener
from settings import DEBUG, API_VERSION, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, MEDIA_FOLDER, SERVER_URL
from sqlalchemy import func

# Logs
logger = logging.getLogger(__name__)
logging.basicConfig(filename='chatmap-api.log', level=logging.INFO)

app = FastAPI(debug=DEBUG)
prefix = f"v{API_VERSION}"
api_router = APIRouter(prefix=f"/{prefix}")

# DB
init_db()

# Scheduler
scheduler = AsyncIOScheduler()

# Access config
origins = [
    "*",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer()

# Create auth token
def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Decode auth token
def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Token generator
@api_router.get("/get-token")
def get_token():
    user_data = {"user_id": str(uuid.uuid4())}
    token = create_token(user_data)
    return {"access_token": token}

# Dependency to extract user from token
def get_current_session(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    return payload

def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> dict:
    payload = decode_token(credentials.credentials)
    return load_session(db, payload["user_id"])

# Get QR code
@api_router.get("/qr", response_class=StreamingResponse)
async def qr(session: dict = Depends(get_current_session)):
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{SERVER_URL}/start-qr?session={session["user_id"]}')
        if response.status_code != 200:
            logger.info(f'Failed to get QR code: {session["user_id"]}')
            raise HTTPException(status_code=502, detail="Failed to get QR code")

        if "image" not in response.headers.get("Content-Type", ""):
            raise HTTPException(status_code=400, detail="URL did not return an image")

        return StreamingResponse(BytesIO(response.content), media_type="image/png")

# Get Status
@api_router.get("/status")
async def status(session: dict = Depends(get_current_session), db: Session = Depends(get_db_session)) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{SERVER_URL}/status?session={session["user_id"]}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to get session")
        status_response = response.json()

        # Update session data
        session["user"] = status_response['user']
        save_session(db, session)

        return {'status': status_response['status']}

# Logout
@api_router.get("/logout")
async def logout(session: dict = Depends(get_current_session), db: Session = Depends(get_db_session)) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{SERVER_URL}/logout?session={session["user_id"]}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to logout")
        remove_session(db, session)
        return {'status': "logged out"}

# Get map points for user
@api_router.get("/map/{user}", response_model=List[PointOut])
async def get_chatmap(
    request: Request,
    user,
    #     session: dict = Depends(get_current_session),
    db: Session = Depends(get_db_session),
):
    points = (
        db.query(
            Point.id,
            Point.message,
            func.ST_X(Point.geom).label("lon"),
            func.ST_Y(Point.geom).label("lat"),
            Point.username,
            Point.time,
            Point.file,
        )
        .filter(Point.user == user)
        .all()
    )
    return [
        {
            "id": point.id,
            "coordinates": [point.lat, point.lon],
            "message": point.message,
            "username": point.username,
            "time": point.time,
            "file": point.file,
        }
        for point in points
    ]

# Get media file (image/jpeg)
@api_router.get("/media")
async def media(filename: str, user: str) -> Dict[str, str]:
    folder_path = os.path.join(MEDIA_FOLDER, user)
    file_path = os.path.join(folder_path, filename)
    if not os.path.isfile(file_path):
        return {"error": "File not found"}
    return FileResponse(path=file_path, media_type="image/jpeg")

# Get Status
@api_router.get("/version")
async def status():
    return {'version': "0.0.1"}

# API Router
app.include_router(api_router)

# On API startup
@api_router.on_event("startup")
async def startup_event():
    global scheduler
    if not os.path.exists("media"):
        os.mkdir("media")
    asyncio.create_task(stream_listener())

# On API shutdown
@api_router.on_event("shutdown")
async def shutdown_event():
    print(f"Shutting down ...")
