from fastapi import APIRouter

from api.v2.routes import maps, media, statuses

router = APIRouter(prefix="/v2")
router.include_router(media.router)
router.include_router(statuses.router)
router.include_router(maps.router)
