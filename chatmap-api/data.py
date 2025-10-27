import os
import logging
import httpx
import base64
from db import add_points, get_db_session
from Crypto.Cipher import AES
from typing import Dict, Sequence, Tuple
from chatmap_py import parser as chatmap_parser
from settings import CHATMAP_ENC_KEY, API_VERSION, MEDIA_FOLDER, API_URL, SERVER_URL

# Logs
logger = logging.getLogger(__name__)
logging.basicConfig(filename='chatmap-data.log', level=logging.INFO)

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

async def download_and_decrypt_file(file: str, user: str) -> str:
    if file:
        # Check: using session could result in dupicates?
        session_folder = os.path.join(MEDIA_FOLDER, user)
        # Create session folder if not exists
        if not os.path.exists(session_folder):
            os.mkdir(session_folder)
        # File to save
        target_file = os.path.join(session_folder, file)
        if not os.path.exists(target_file):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f'{SERVER_URL}/media/{file}?user={user}')
                    response.raise_for_status()  # Raise for 4xx/5xx
                with open(target_file, "wb") as f:
                    if len(response.content) > 0:
                        f.write(response.content)
                        logger.info(f'File saved: {target_file}')
                    else:
                        logger.info(f'File is empty: {target_file}')

            except httpx.HTTPError as e:
                logger.error(f"Failed to download: {str(e)}")

        url = f"{API_URL}/{prefix}/media?user={user}&filename={file}"
        return url
    return None

async def process_chat_entries(
    user: str,
    entries: Sequence[Tuple[str, Dict[str, bytes]]]
) -> None:
    logger.info(f'get_chatmap: session {user}')
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
        coords = feature.get("geometry").get("coordinates")
        props = feature.get("properties")
        geom = f"POINT({coords[0]} {coords[1]})"
        message = decrypt_message(props.get("message"))
        file = await download_and_decrypt_file(props.get("file"), user)
        if props.get("id") is not None:
            points.append({
                "id": props.get("id"),
                "geom": geom,
                "message": message,
                "file": file,
                "time": props.get("time"),
                "username": props.get("username"),
                "user": user,
            })
    add_points(db=db, points=points)
