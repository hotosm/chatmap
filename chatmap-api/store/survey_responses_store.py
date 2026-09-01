import logging

from sqlalchemy.exc import SQLAlchemyError
from db import session_scope, Base
from results.error import StoreUnavailable
from sqlalchemy import Column, String, select, delete
from sqlalchemy.dialects.postgresql import insert, JSONB

logger = logging.getLogger(__name__)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"
    map_id = Column(String, primary_key=True)
    point_id = Column(String, primary_key=True)
    answers = Column(JSONB, nullable=False, default=dict)


class SurveyResponsesStore:
    @classmethod
    async def add_response(cls, map_id: str, point_id: str, question_id: str, question: str, answer: str) -> None:
        with session_scope() as db:
            try:
                query = insert(SurveyResponse).values(
                    map_id=map_id,
                    point_id=point_id,
                    answers={question_id: {"question": question, "answer": answer}},
                )
                # `||` merges the two JSONB objects; the incoming question_id wins.
                query = query.on_conflict_do_update(
                    index_elements=["map_id", "point_id"],
                    set_={"answers": SurveyResponse.answers.op("||")(query.excluded.answers)},
                )
                db.execute(query)
                db.commit()
                logger.debug(f"Survey response saved for point '{point_id}' on map '{map_id}'")
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Save survey response for point '{point_id}' on map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def answered_question_ids(cls, map_id: str, point_id: str) -> set[str]:
        with session_scope() as db:
            try:
                query = select(SurveyResponse.answers).where(
                    SurveyResponse.map_id == map_id,
                    SurveyResponse.point_id == point_id,
                )
                answers = db.execute(query).scalar_one_or_none() or {}
                return set(answers.keys())
            except SQLAlchemyError as error:
                logger.error(f"Fetch survey responses for point '{point_id}' on map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def responses_for_points(cls, map_id: str, point_ids: list[str]) -> dict[str, list[dict]]:
        if not point_ids:
            return {}

        with session_scope() as db:
            try:
                query = select(SurveyResponse.point_id, SurveyResponse.answers).where(
                    SurveyResponse.map_id == map_id,
                    SurveyResponse.point_id.in_(point_ids),
                )
                rows = db.execute(query).all()
                return {
                    point_id: [
                        {"question": entry["question"], "answer": entry["answer"]}
                        for entry in (answers or {}).values()
                    ]
                    for point_id, answers in rows
                }
            except SQLAlchemyError as error:
                logger.error(f"Fetch survey responses for {len(point_ids)} point(s) failed with: '{error}'")
                raise StoreUnavailable

    @classmethod
    async def delete_responses(cls, map_id: str, point_id: str) -> None:
        with session_scope() as db:
            try:
                db.execute(
                    delete(SurveyResponse).where(
                        SurveyResponse.map_id == map_id,
                        SurveyResponse.point_id == point_id,
                    )
                )
                db.commit()
                logger.debug(f"Survey responses deleted for point '{point_id}' on map '{map_id}'")
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Delete survey responses for point '{point_id}' on map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable
