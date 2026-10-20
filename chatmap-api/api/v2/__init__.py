from fastapi import APIRouter

from api.v2.routes import keys, media, points, statuses, tag_changes

router = APIRouter(prefix="/v2")
router.include_router(media.router)
router.include_router(statuses.router)
router.include_router(points.router)
router.include_router(tag_changes.router)
router.include_router(keys.router)
