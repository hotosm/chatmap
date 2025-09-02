import os
import logging
import httpx
import base64
import json
from db import UserChatMap, get_db_session
from Crypto.Cipher import AES
from typing import Dict, Sequence, Tuple
from chatmap_py import parser as chatmap_parser
from sqlalchemy.orm import Session
from settings import MEDIA_FOLDER, API_URL, CHATMAP_ENC_KEY, SERVER_URL, API_VERSION

# Logs
logger = logging.getLogger(__name__)
logging.basicConfig(filename='chatmap-data.log', level=logging.INFO)

# Prefix for media files
prefix = f"v{API_VERSION}"

def decrypt(encoded_data: str) -> str:
    key = CHATMAP_ENC_KEY.encode('utf-8')
    raw = base64.b64decode(encoded_data)
    nonce_size = 12
    nonce = raw[:nonce_size]
    ciphertext = raw[nonce_size:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext[:-16], ciphertext[-16:])
    return plaintext.decode('utf-8')

# Merge two GeoJSON objects, prevent duplicates
def merge_geojson(currentGeoJSON, newGeoJSON):
    merged = []
    for item in newGeoJSON["features"]:
        merged.append(item)
    for item in currentGeoJSON["features"]:
        if not any(i["properties"]["id"] == item["properties"]["id"] for i in merged):
            if not any(i["properties"]["related"] == item["properties"]["id"] for i in merged):
                merged.append(item)
    return merged

async def process_chat_entries(
    user: str,
    entries: Sequence[Tuple[str, Dict[str, bytes]]]
) -> None:
    logger.info(f'get_chatmap: session {user}')
    db = get_db_session()
    # Convert to list of dictionaries and add index as id
    data = [
        {
            **{bytes.decode(k): bytes.decode(v) \
                if isinstance(v, bytes) \
                    else v for k, v in entry.items()},
            'id': idx
        }
        for idx, (_, entry) in enumerate(entries)
    ]

    geoJSON = {}
    # Get GeoJSON from ChatMap
    try:
        geoJSON = chatmap_parser.streamParser(data)
    except Exception as e:
        print(f"Error parsing chat: {e}")

    if 'features' in geoJSON:
        filtered_features = []
        for feature in geoJSON['features']:
            # Text message
            if 'message' in feature['properties'] and feature['properties']['message'] != "":
                # Decrypt it
                feature['properties']['message'] = decrypt(feature['properties']['message'])
                filtered_features.append(feature)

            # Image file
            if 'file' in feature['properties'] and feature['properties']['file'] != "":
                # and feature['properties']['related'] not in related_ids:
                # If image, get the decrypted file from the connector sever
                # and save it to local directory
                if feature['properties']['file'].endswith(".jpg"):
                    filename = feature['properties']['file']

                    # Check: using session could result in dupicates?
                    session_folder = os.path.join(MEDIA_FOLDER, user)

                    # Create session folder if not exists
                    if not os.path.exists(session_folder):
                        os.mkdir(session_folder)

                    # File to save
                    target_file = os.path.join(session_folder, f"{filename}")

                    # If file was not saved previously, download decrypted image
                    # from connector server and save it to disk
                    if not os.path.exists(target_file):
                        logger.info(f'Trying to save media file: {target_file}')
                        try:
                            async with httpx.AsyncClient() as client:
                                response = await client.get(f'{SERVER_URL}/media/{filename}?user={user}')
                                response.raise_for_status()  # Raise for 4xx/5xx
                            with open(target_file, "wb") as f:
                                if len(response.content) > 0:
                                    f.write(response.content)
                                    logger.info(f'Media file saved: {target_file}')
                                else:
                                    logger.info(f'Media file is empty: {target_file}')

                        except httpx.HTTPError as e:
                            logger.error(f"Failed to download: {str(e)}")

                    # Image URL
                    url = f"{API_URL}/{prefix}/media?user={user}&filename={filename}"
                    feature['properties']['file'] = url
                    filtered_features.append(feature)

        try:
            userChatmap = db.query(UserChatMap).filter(UserChatMap.id == user).first()
            if userChatmap:
                # Merge new GeoJSON with existing one and update DB
                currentGeoJSON = json.loads(userChatmap.geojson)
                if 'features' in filtered_features and len(filtered_features['features']) > 0:
                    mergedGeoJSON = {
                        "type": "FeatureCollection",
                        "features": merge_geojson(currentGeoJSON, filtered_features)
                    }
                    userChatmap.geojson = json.dumps(mergedGeoJSON)
                    db.commit()
                    db.refresh(userChatmap)
                    return
                else:
                    return
            else:
                # Create new entry
                newUserChatmap = UserChatMap(id=user, geojson=json.dumps(filtered_features))
                db.add(newUserChatmap)
                db.commit()
                db.refresh(newUserChatmap)
        except Exception as e:
            print(f"Error getting chatmap: {e}")
            raise Exception(status_code=500, detail=str(e))