import logging

from sqlalchemy.exc import SQLAlchemyError

from db import add_survey_response, get_db_session
from results.error import StoreUnavailable

logger = logging.getLogger(__name__)


class SurveyResponsesStore:
    @classmethod
    async def add_response(cls, point_id: str, question: str, answer: str) -> None:
        db = get_db_session()
        try:
            add_survey_response(db=db, point_id=point_id, question=question, answer=answer)
            logger.debug(f"Survey response saved for point '{point_id}'")
        except SQLAlchemyError as error:
            db.rollback()
            logger.error(f"Save survey response for point '{point_id}' failed with: '{error}'")
            raise StoreUnavailable
