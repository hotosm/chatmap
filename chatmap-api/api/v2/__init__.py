from fastapi import APIRouter

from api.v2.routes import media, points

router = APIRouter(prefix="/v2")
router.include_router(media.router)
router.include_router(points.router)
