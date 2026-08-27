import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# main.py wires up hotosm_auth_fastapi at import time, which requires these to
# be set even though these tests never talk to Hanko.
os.environ.setdefault("HANKO_API_URL", "http://localhost:8002")
os.environ.setdefault("COOKIE_SECRET", "dev-secret-key-min-32-bytes-long!")

from main import map_response


def _point(point_id="p-1", file=None):
    return SimpleNamespace(
        id=point_id, message="a note", lat=1.0, lon=2.0, username="mapper",
        time=datetime(2026, 8, 21, 9, 48), file=file, removed=False, tags="",
    )


def _map(map_id="map-1"):
    return SimpleNamespace(
        id=map_id, sharing=SimpleNamespace(value="public"), name="A map",
        description=None, is_live=False,
    )


def _db_with_points(points):
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = points
    return db


async def test_each_feature_carries_its_own_survey_answers():
    db = _db_with_points([_point("p-1"), _point("p-2")])
    answers = {
        "p-1": [
            {"question": "Smoothness", "answer": "intermediate"},
            {"question": "Comments", "answer": "water leaks"},
        ]
    }

    with patch("main.SurveyResponsesStore.responses_for_points", AsyncMock(return_value=answers)) as fetch:
        result = await map_response(db, _map(), owner=True)

    fetch.assert_awaited_once_with(["p-1", "p-2"])
    by_id = {feature["properties"]["id"]: feature["properties"]["survey"] for feature in result["features"]}
    assert by_id["p-1"] == answers["p-1"]


async def test_a_point_without_answers_gets_an_empty_survey():
    db = _db_with_points([_point("p-1")])

    with patch("main.SurveyResponsesStore.responses_for_points", AsyncMock(return_value={})):
        result = await map_response(db, _map(), owner=True)

    assert result["features"][0]["properties"]["survey"] == []


async def test_a_map_without_points_asks_for_no_survey_responses():
    db = _db_with_points([])

    with patch("main.SurveyResponsesStore.responses_for_points", AsyncMock(return_value={})) as fetch:
        result = await map_response(db, _map(), owner=True)

    fetch.assert_awaited_once_with([])
    assert result["features"] == []
