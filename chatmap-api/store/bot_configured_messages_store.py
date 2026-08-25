import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from db import get_db_session, Base, Map
from results.error import StoreUnavailable
from sqlalchemy.dialects.postgresql import JSONB
from bot.configured_messages import (
    BotStep, BotConfiguredMessages, BotMaxAttemptsMessages,
    BotMessage as DomainBotMessage,
)
from sqlalchemy import (
    Column, String, select, ForeignKey,
    Enum as SqlEnum, Integer, delete,
)

logger = logging.getLogger(__name__)


class BotMessage(Base):
    __tablename__ = "bot_configured_messages"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    map_id = Column(String, ForeignKey("maps.id"), index=True, nullable=False)
    bot_step = Column(
        SqlEnum(
            BotStep, name="bot_step",
            values_callable=lambda enum: [member.value for member in enum]
        ),
        nullable=False,
    )
    # Ordering among SINGLE_CHOICE questions; null for every other kind
    position = Column(Integer, nullable=True)
    content = Column(String, nullable=False, default="")
    error_message = Column(String, nullable=True)
    options = Column(JSONB, nullable=False, default=list)
    # The three below are only set on the MAX_ATTEMPTS row; null for every other kind
    max_attempts_quantity = Column(Integer, nullable=True)
    to_restart = Column(String, nullable=True)
    to_cancel = Column(String, nullable=True)


class BotConfiguredMessagesStore:
    @classmethod
    async def get_configured_messages_for(cls, device: str) -> BotConfiguredMessages:
        db = get_db_session()
        try:
            query = (
                select(BotMessage)
                .join(Map, Map.id == BotMessage.map_id)
                .where(Map.owner_id == device)
                .order_by(BotMessage.position.asc().nullsfirst())
            )
            rows = list(db.execute(query).scalars())

            attempts_row = next((row for row in rows if row.bot_step == BotStep.MAX_ATTEMPTS))
            if attempts_row:
                max_attempts_messages = BotMaxAttemptsMessages(
                    max_attempts_quantity=attempts_row.max_attempts_quantity,
                    notify_message=attempts_row.content,
                    to_restart=attempts_row.to_restart,
                    to_cancel=attempts_row.to_cancel,
                )
            else:
                max_attempts_messages = BotMaxAttemptsMessages(
                    max_attempts_quantity=0, notify_message="", to_restart="", to_cancel="",
                )

            return BotConfiguredMessages(
                max_attempts_messages=max_attempts_messages,
                messages=[
                    DomainBotMessage(
                        id=row.id,
                        bot_step=row.bot_step,
                        prompt=row.content,
                        error_message=row.error_message or "",
                        options=row.options or [],
                    )
                    for row in rows
                    if row.bot_step != BotStep.MAX_ATTEMPTS
                ],
            )
        except SQLAlchemyError as error:
            logger.error(f"Fetch configured bot messages for device '{device}' failed with: '{error}'")
            raise StoreUnavailable


def get_configured_messages(map_id: str) -> list[BotMessage]:
    db = get_db_session()
    query = (
        select(BotMessage)
        .where(BotMessage.map_id == map_id)
        .order_by(BotMessage.position.asc().nullsfirst())
    )
    return list(db.execute(query).scalars())


def update_configured_messages(map_id: str, messages: list[dict]) -> list[BotMessage]:
    db = get_db_session()
    existing = {row.id: row for row in get_configured_messages(map_id)}
    kept = set()

    for message in messages:
        message_id = message.get("id")
        row = existing.get(message_id) if message_id is not None else None

        if row is None:
            row = BotMessage(map_id=map_id)
            db.add(row)
        else:
            kept.add(row.id)

        row.bot_step = BotStep(message["bot_step"])
        row.position = message.get("position")
        row.content = message.get("prompt") or ""
        row.error_message = message.get("error_message")
        row.options = message.get("options") or []
        row.max_attempts_quantity = message.get("max_attempts_quantity")
        row.to_restart = message.get("to_restart")
        row.to_cancel = message.get("to_cancel")

    stale = [row_id for row_id in existing if row_id not in kept]
    if stale:
        db.execute(delete(BotMessage).where(BotMessage.id.in_(stale)))

    db.commit()
    return get_configured_messages(map_id)
