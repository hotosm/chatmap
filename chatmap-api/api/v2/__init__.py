from fastapi import APIRouter

from api.v2.routes import keys, media, points, tags

router = APIRouter(prefix="/v2")
router.include_router(media.router)
router.include_router(points.router)
router.include_router(tags.router)
router.include_router(keys.router)
