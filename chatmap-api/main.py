import os
import httpx
import logging
import redis.asyncio as redis
import time
import json
import uuid
import base64
from Crypto.Cipher import AES
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict
from models import GeoJson
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from chatmap_py import parser as chatmap_parser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import UserChatMap, Base, engine, SessionLocal, init_db, load_session, save_session
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

# Logs
logger = logging.getLogger(__name__)
logging.basicConfig(filename='chatmap-api.log', level=logging.INFO)

# Debug
DEBUG = False

## Security
SECRET_KEY = os.getenv("CHATMAP_SECRET_KEY", "4sup3rs3cret5up3rdummykey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
CHATMAP_ENC_KEY=os.getenv("CHATMAP_ENC_KEY", "0123456789ABCDEF0123456789ABCDEF")

# Configure Redis connection
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Redis key for filtering
STREAM_KEY = "wa-messages"
# Expiring time for messages (in minutes)
EXPIRING_MIN = 30
EXPIRING_MIN_MS = EXPIRING_MIN * 60 * 1000

# Linked devices server
server_url = os.getenv("SERVER_URL", "http://localhost:8001")

# DB
init_db()

# API
app = FastAPI()

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

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def decrypt(encoded_data: str) -> str:
    key = CHATMAP_ENC_KEY.encode('utf-8')
    raw = base64.b64decode(encoded_data)
    nonce_size = 12
    nonce = raw[:nonce_size]
    ciphertext = raw[nonce_size:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext[:-16], ciphertext[-16:])
    return plaintext.decode('utf-8')

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
@app.get("/get-token")
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
    db: Session = Depends(get_db)
) -> dict:
    payload = decode_token(credentials.credentials)
    return load_session(db, payload["user_id"])


# Get QR code
@app.get("/qr", response_class=StreamingResponse)
async def qr(session: dict = Depends(get_current_session)):
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{server_url}/start-qr?session={session['user_id']}')
        if response.status_code != 200:
            logger.info(f'Failed to get QR code: {session['user_id']}')
            raise HTTPException(status_code=502, detail="Failed to get QR code")

        if "image" not in response.headers.get("Content-Type", ""):
            raise HTTPException(status_code=400, detail="URL did not return an image")

        return StreamingResponse(BytesIO(response.content), media_type="image/png")

# Get Status
@app.get("/status")
async def status(session: dict = Depends(get_current_session), db: Session = Depends(get_db)) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{server_url}/status?session={session['user_id']}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to get session")
        status_response = response.json()

        # Update session data
        session["user"] = status_response['user']
        save_session(db, session)

        return {'status': status_response['status']}

# Logout
@app.get("/logout")
async def status(session: dict = Depends(get_current_session)) -> Dict[str, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{server_url}/logout?session={session['user_id']}')
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to logout")
        return {'status': "logged out"}

# Cleanup old messages
async def cleanup(user_id: str):
    cutoff_time_ms = int(time.time() * 1000) - EXPIRING_MIN_MS
    cutoff_id = f"{cutoff_time_ms}-0"
    entries = await redis_client.xrange(f"{STREAM_KEY}:{user_id}", min='-', max=cutoff_id)
    # Remove data older than (EXPIRING_MIN_MS) minutes
    for entry_id, _ in entries:
        await redis_client.xdel(f"{STREAM_KEY}:{user_id}", entry_id)
    logger.info(f'cleanup: {len(entries)} messages deleted')

# Merge two GeoJSON objects, prevent duplicates
def merge_geojson(currentGeoJSON, newGeoJSON):
    merged = []
    for item in newGeoJSON["features"]:
        merged.append(item)
    for item in currentGeoJSON["features"]:
        if not any(i["properties"]["id"] == item["properties"]["id"] for i in merged):
            merged.append(item)
    return merged

# Get GeoJSON generated by ChatMap
@app.get("/chatmap")
async def get_chatmap(session: dict = Depends(get_current_session), db: Session = Depends(get_db)) -> GeoJson:
    logger.info(f'get_chatmap: session {session['user_id']}')
    try:
        # Get all available messages
        entries = await redis_client.xrange(f"{STREAM_KEY}:{session['user_id']}", min='-', max='+')
        # Cleanup old messages
        await cleanup(session['user_id'])
    except Exception as e:
        print(f"Error getting entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    data = [
        {bytes.decode(k): bytes.decode(v) if isinstance(v, bytes) else v
        for k, v in entry.items()}
        for entry_id, entry in entries
    ]
    geoJSON = {}

    # Get GeoJSON from ChatMap
    try:
        geoJSON = chatmap_parser.streamParser(data)
    except Exception as e:
        print(f"Error parsing chat: {e}")

    for feature in geoJSON['features']:
        if 'message' in feature['properties'] and feature['properties']['message'] != "":
            feature['properties']['message'] = decrypt(feature['properties']['message'])

    # Look for existing entries for same user in DB
    if 'user' in session:
        try:
            userChatmap = db.query(UserChatMap).filter(UserChatMap.id == session['user']).first()
            if userChatmap:
                # Merge new GeoJSON with existing one and update DB
                currentGeoJSON = json.loads(userChatmap.geojson)
                if 'features' in geoJSON and len(geoJSON['features']) > 0:
                    mergedGeoJSON = {
                        "type": "FeatureCollection",
                        "features": merge_geojson(currentGeoJSON, geoJSON)
                    }
                    userChatmap.geojson = json.dumps(mergedGeoJSON)
                    db.commit()
                    db.refresh(userChatmap)
                    return mergedGeoJSON
                else:
                    return json.loads(userChatmap.geojson)
            else:
                # Create new entry
                newUserChatmap = UserChatMap(id=session['user'], geojson=json.dumps(geoJSON))
                db.add(newUserChatmap)
                db.commit()
                db.refresh(newUserChatmap)
        except Exception as e:
            print(f"Error getting chatmap: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return geoJSON

# Get all sessions
async def get_sessions():
    sessions = await redis_client.scan(0, match="wa-messages:*", type="stream")
    return [item[0].decode('utf-8').replace("wa-messages:", "") for item in sessions if type(item) != int]

# Update all sessions every (EXPIRING_MIN) minutes
@scheduler.scheduled_job('interval', minutes=EXPIRING_MIN)
async def update():
    sessions = get_sessions()
    for session in sessions:
        await get_chatmap(session)

# On API startup
def on_startup():
    global scheduler
    try:
        Base.metadata.create_all(bind=engine)
        scheduler.start()
    except Exception as e:
        print(f"Error starting scheduler: {e}")

# On API shutdown
def on_shutdown():
    global scheduler
    try:
        scheduler.shutdown(wait=True)
    except Exception as e:
        print(f"Error shutting down scheduler: {e}")

# ----- (FOR DEBUGGING) -----

# if DEBUG:
#     # Get raw messages
#     @app.get("/messages")
#     async def messages(session: dict = Depends(get_current_session)):
#         try:
#             entries = await redis_client.xrange(f"{STREAM_KEY}:{session['user_id']}", min='-', max='+')
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))
#         data = [{"id": entry_id, **fields} for entry_id, fields in entries]
#         return data

#     # Get user session
#     @app.get("/me")
#     def read_me(session: dict = Depends(get_current_session)):
#         return session
