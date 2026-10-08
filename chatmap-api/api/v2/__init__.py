from fastapi import APIRouter

from api.v2.routes import media, statuses

router = APIRouter(prefix="/v2")
router.include_router(media.router)
router.include_router(statuses.router)
