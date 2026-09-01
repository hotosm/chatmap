from unittest.mock import MagicMock, patch

import pytest

from results.error import StoreUnavailable
from store.survey_responses_store import SurveyResponsesStore

# Stored as {question_id: {question, answer}}; the map only wants question/answer.
_ROW_ANSWERS = {
    "q-1": {"question": "Smoothness", "answer": "intermediate"},
    "q-2": {"question": "Comments", "answer": "water leaks"},
}


def _db_returning(rows):
    db = MagicMock()
    db.execute.return_value.all.return_value = rows
    return db


def _db_scalar(value):
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = value
    return db


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.survey_responses_store.session_scope", scope)


async def test_returns_nothing_without_point_ids():
    with patch("store.survey_responses_store.session_scope") as session_scope:
        result = await SurveyResponsesStore.responses_for_points("map-1", [])

    assert result == {}
    session_scope.assert_not_called()


async def test_keys_answers_by_point_id_dropping_question_id():
    db = _db_returning([("p-1", _ROW_ANSWERS)])

    with _patch_scope(db):
        result = await SurveyResponsesStore.responses_for_points("map-1", ["p-1", "p-2"])

    assert result == {
        "p-1": [
            {"question": "Smoothness", "answer": "intermediate"},
            {"question": "Comments", "answer": "water leaks"},
        ]
    }


async def test_points_without_responses_are_absent():
    db = _db_returning([("p-1", _ROW_ANSWERS)])

    with _patch_scope(db):
        result = await SurveyResponsesStore.responses_for_points("map-1", ["p-1", "p-2"])

    assert "p-2" not in result


async def test_a_row_with_empty_answers_maps_to_an_empty_list():
    db = _db_returning([("p-1", None)])

    with _patch_scope(db):
        result = await SurveyResponsesStore.responses_for_points("map-1", ["p-1"])

    assert result == {"p-1": []}


async def test_answered_question_ids_are_the_stored_keys():
    db = _db_scalar(_ROW_ANSWERS)

    with _patch_scope(db):
        result = await SurveyResponsesStore.answered_question_ids("map-1", "p-1")

    assert result == {"q-1", "q-2"}


async def test_no_row_means_no_answered_questions():
    db = _db_scalar(None)

    with _patch_scope(db):
        result = await SurveyResponsesStore.answered_question_ids("map-1", "p-1")

    assert result == set()


async def test_a_database_error_raises_store_unavailable():
    from sqlalchemy.exc import SQLAlchemyError

    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await SurveyResponsesStore.responses_for_points("map-1", ["p-1"])
