from fastapi import APIRouter, Response

from api.v2.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health")
async def health(response: Response) -> HealthResponse:
    response.headers["Cache-Control"] = "no-store"

    return HealthResponse(status="ok")
