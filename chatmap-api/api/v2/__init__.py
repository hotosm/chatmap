from fastapi import APIRouter

from api.v2.routes import contributors, health, invitations, keys, maps, media, points, tags

router = APIRouter(prefix="/v2")
router.include_router(contributors.router)
router.include_router(health.router)
router.include_router(invitations.router)
router.include_router(maps.router)
router.include_router(media.router)
router.include_router(points.router)
router.include_router(tags.router)
router.include_router(keys.router)
