"""
This module processes chat messages from a Redis stream, decrypts them,
downloads associated media files, parses geolocation data using ChatMap,
and stores the resulting map points in a database.
"""

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
    """
    Decrypts a base64-encoded AES-GCM encrypted message.

    Args:
        encoded_data (str): Base64-encoded string containing the encrypted message.

    Returns:
        str: Decrypted plaintext message.
    """
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
    """
    Downloads a media file from the server if not already present locally,
    and returns the public URL for accessing it.

    Args:
        file (str): Filename of the media file.
        user (str): User ID associated with the media file.

    Returns:
        str: Public URL to access the media file.
    """
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
    """
    Processes a batch of chat entries from Redis, extracts geolocation data,
    decrypts messages, downloads media, and stores the points in the database.

    Args:
        user (str): Identifier for the user whose chat entries are being processed.
        entries (Sequence[Tuple[str, Dict[str, bytes]]]): List of Redis stream entries,
            each entry is a tuple of (entry_id, fields).
    """
    logger.debug(f'get_chatmap: session {user}')
    db = get_db_session()

    # Convert Redis entries to indexed list of dictionaries
    data = [{ **{bytes.decode(k): bytes.decode(v) \
        if isinstance(v, bytes) else v for k, v in entry[1].items()}} for (_, entry) in enumerate(entries)]

    # Parse chat data into GeoJSON format using ChatMap
    geoJSON = {}
    try:
        geoJSON = chatmap_parser.streamParser(data)
    except Exception as e:
        print(f"Error parsing chat: {e}")

    # Create Points from Features in GeoJSON
    points = []
    for feature in geoJSON.get('features'):
        logging.debug("Processing feature ...")
        coords = feature.get("geometry").get("coordinates")
        props = feature.get("properties")
        geom = f"POINT({coords[0]} {coords[1]})"
        message = decrypt_message(props.get("message"))
        file = await download_media_file(props.get("file"), user)
        if props.get("id") is not None:
            logger.debug(f"Adding point id {props.get("id")}")
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
