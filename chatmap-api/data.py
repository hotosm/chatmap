import os
import logging
import httpx
import base64
import hashlib
from db import add_points, get_db_session, Map
from Crypto.Cipher import AES
from typing import Dict, Sequence, Tuple
from chatmap_py import parser as chatmap_parser
from settings import CHATMAP_ENC_KEY, API_VERSION, MEDIA_FOLDER, API_URL, SERVER_URL

# Logs
logger = logging.getLogger(__name__)

# Prefix for media files
prefix = f"v{API_VERSION}"

def decrypt_message(encoded_data: str) -> str:
    if encoded_data:
        key = CHATMAP_ENC_KEY.encode('utf-8')
        raw = base64.b64decode(encoded_data)
        nonce_size = 12
        nonce = raw[:nonce_size]
        ciphertext = raw[nonce_size:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext[:-16], ciphertext[-16:])
        return plaintext.decode('utf-8')

# Download and save media files
async def download_media_file(file: str, user: str) -> str:
    if file:
        file_ext = file.split('.')[-1]
        file_name = f"{hashlib.sha256(f"{user}-{file}".encode()).hexdigest()}.{file_ext}"
        target_file = os.path.join(MEDIA_FOLDER, file_name)
        url = f"{API_URL}/{prefix}/media?filename={file_name}"
        if not os.path.exists(target_file):
            try:
                # Download file from IM connector server
                async with httpx.AsyncClient() as client:
                    response = await client.get(f'{SERVER_URL}/media/{file}?user={user}')
                    response.raise_for_status()  # Raise for 4xx/5xx
                # Save file
                if len(response.content) > 0:
                    with open(target_file, "wb") as f:
                        f.write(response.content)
                        logger.debug(f'File saved: {target_file}')
                else:
                    logger.warning(f'File is empty: {file}')

            except httpx.HTTPError as e:
                logger.error(f"Failed to download: {str(e)}")
        else:
            logger.info(f'File exists: {target_file}')
        return url
    else:
        logger.debug(f'No file')
    return None

async def process_chat_entries(
    user: str,
    entries: Sequence[Tuple[str, Dict[str, bytes]]]
) -> None:
    logger.debug(f'get_chatmap: session {user}')
    db = get_db_session()

    # Convert to list of dictionaries (from Redis) and add index as id
    data = [{ **{bytes.decode(k): bytes.decode(v) \
        if isinstance(v, bytes) else v for k, v in entry[1].items()}} for (_, entry) in enumerate(entries)]

    # Get GeoJSON from ChatMap
    geoJSON = {}
    try:
        geoJSON = chatmap_parser.streamParser(data)
    except Exception as e:
        print(f"Error parsing chat: {e}")

    # Create Points from Features
    points = []
    for feature in geoJSON.get('features'):
        logging.debug("Processing feature ...")
        coords = feature.get("geometry").get("coordinates")
        props = feature.get("properties")
        geom = f"POINT({coords[0]} {coords[1]})"
        message = decrypt_message(props.get("message"))
        file = await download_media_file(props.get("file"), user)
        if props.get("id") is not None:
            logger.debug("Adding point")
            logger.debug(f"id {props.get("id")}")
            logger.debug(f"geom {geom}")
            logger.debug(f"message {message}")
            logger.debug(f"file {file}")
            logger.debug(f"time {props.get("time")}")
            logger.debug(f"username {props.get("username")}")
            logger.debug(f"user {user}")
            points.append({
                "id": props.get("id"),
                "geom": geom,
                "message": message,
                "file": file,
                "time": props.get("time"),
                "username": props.get("username"),
            })
    if len(points) > 0:
        add_points(db=db, points=points, user_id=user)
