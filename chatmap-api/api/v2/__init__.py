from fastapi import APIRouter

from api.v2.routes import keys, media, messages, points, tags
from settings import ENABLE_GROUP_MESSAGES

router = APIRouter(prefix="/v2")
router.include_router(media.router)
router.include_router(points.router)
router.include_router(tags.router)
router.include_router(keys.router)
# Without the switch nothing of the chat groups is kept, not even their names
if ENABLE_GROUP_MESSAGES:
    router.include_router(messages.router)
