import inspect

from fastapi import Response

from api.v2 import router
from api.v2.routes.health import health


# ---- GET /v2/health ----

async def test_health_reports_ok():
    result = await health(Response())

    assert result.status == "ok"


async def test_health_forbids_caching_the_answer():
    response = Response()

    await health(response)

    assert response.headers["Cache-Control"] == "no-store"


def test_health_needs_no_credentials_and_no_database():
    assert list(inspect.signature(health).parameters) == ["response"]


def test_health_is_served_under_v2():
    assert any(route.path == "/v2/health" and "GET" in route.methods for route in router.routes)
