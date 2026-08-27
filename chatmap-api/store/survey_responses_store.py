import logging

from sqlalchemy.exc import SQLAlchemyError
from db import get_db_session
from results.error import StoreUnavailable
from sqlalchemy import Column, String, select
from sqlalchemy.dialects.postgresql import insert, JSONB
from sqlalchemy.orm import declarative_base, Session

logger = logging.getLogger(__name__)
Base = declarative_base()


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    point_id = Column(String, primary_key=True)
    answers = Column(JSONB, nullable=False, default=list)


class SurveyResponsesStore:
    @classmethod
    async def add_response(cls, point_id: str, question_id: str, question: str, answer: str) -> None:
        db = get_db_session()
        try:
            query = insert(SurveyResponse).values(
                point_id=point_id,
                answers=[{"question_id": question_id, "question": question, "answer": answer}],
            )
            query = query.on_conflict_do_update(
                index_elements=["point_id"],
                set_={"answers": SurveyResponse.answers.op("||")(query.excluded.answers)},
            )
            db.execute(query)
            db.commit()
            logger.debug(f"Survey response saved for point '{point_id}'")
        except SQLAlchemyError as error:
            db.rollback()
            logger.error(f"Save survey response for point '{point_id}' failed with: '{error}'")
            raise StoreUnavailable

    @classmethod
    async def answered_question_ids(cls, point_id: str) -> set[str]:
        db = get_db_session()
        try:
            query = select(SurveyResponse.answers).where(SurveyResponse.point_id == point_id)
            answers = db.execute(query).scalar_one_or_none() or []
            return {answer["question_id"] for answer in answers if answer.get("question_id")}
        except SQLAlchemyError as error:
            logger.error(f"Fetch survey responses for point '{point_id}' failed with: '{error}'")
            raise StoreUnavailable

    @classmethod
    async def responses_for_points(cls, point_ids: list[str]) -> dict[str, list[dict]]:
        if not point_ids:
            return {}

        db = get_db_session()
        try:
            query = select(SurveyResponse.point_id, SurveyResponse.answers).where(
                SurveyResponse.point_id.in_(point_ids)
            )
            rows = db.execute(query).all()
            return {
                point_id: [
                    {"question": answer["question"], "answer": answer["answer"]}
                    for answer in (answers or [])
                ]
                for point_id, answers in rows
            }
        except SQLAlchemyError as error:
            logger.error(f"Fetch survey responses for {len(point_ids)} point(s) failed with: '{error}'")
            raise StoreUnavailable
