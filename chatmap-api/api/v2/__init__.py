from fastapi import APIRouter

from api.v2.routes import media

router = APIRouter(prefix="/v2")
router.include_router(media.router)
