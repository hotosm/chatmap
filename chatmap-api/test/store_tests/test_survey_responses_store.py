from unittest.mock import MagicMock, patch

import pytest

from results.error import StoreUnavailable
from store.survey_responses_store import SurveyResponsesStore

# The store items store question_id alongside the text; the map only wants the
# question and answer, in the order they were answered.
_ROW_ANSWERS = [
    {"question_id": "q-1", "question": "Smoothness", "answer": "intermediate"},
    {"question_id": "q-2", "question": "Comments", "answer": "water leaks"},
]


def _db_returning(rows):
    db = MagicMock()
    db.execute.return_value.all.return_value = rows
    return db


async def test_returns_nothing_without_point_ids():
    with patch("store.survey_responses_store.get_db_session") as get_db_session:
        result = await SurveyResponsesStore.responses_for_points([])

    assert result == {}
    get_db_session.assert_not_called()


async def test_keys_answers_by_point_id_dropping_question_id():
    db = _db_returning([("p-1", _ROW_ANSWERS)])

    with patch("store.survey_responses_store.get_db_session", return_value=db):
        result = await SurveyResponsesStore.responses_for_points(["p-1", "p-2"])

    assert result == {
        "p-1": [
            {"question": "Smoothness", "answer": "intermediate"},
            {"question": "Comments", "answer": "water leaks"},
        ]
    }


async def test_points_without_responses_are_absent():
    db = _db_returning([("p-1", _ROW_ANSWERS)])

    with patch("store.survey_responses_store.get_db_session", return_value=db):
        result = await SurveyResponsesStore.responses_for_points(["p-1", "p-2"])

    assert "p-2" not in result


async def test_a_row_with_empty_answers_maps_to_an_empty_list():
    db = _db_returning([("p-1", None)])

    with patch("store.survey_responses_store.get_db_session", return_value=db):
        result = await SurveyResponsesStore.responses_for_points(["p-1"])

    assert result == {"p-1": []}


async def test_a_database_error_raises_store_unavailable():
    from sqlalchemy.exc import SQLAlchemyError

    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with patch("store.survey_responses_store.get_db_session", return_value=db):
        with pytest.raises(StoreUnavailable):
            await SurveyResponsesStore.responses_for_points(["p-1"])
