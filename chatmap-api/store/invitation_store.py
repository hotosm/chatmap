import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, select, text, update
from sqlalchemy.exc import SQLAlchemyError

from db import Base, Map, session_scope
from results.error import MapNotFound, StoreUnavailable

logger = logging.getLogger(__name__)


class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    map_id = Column(String, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "uq_invitations_one_current_per_map",
            "map_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _lock_owner_of(db, map_id: str) -> str | None:
    query = select(Map.owner_id).where(Map.id == map_id).with_for_update()

    return db.execute(query).scalar_one_or_none()


def _revoke_current(db, map_id: str, now: datetime) -> None:
    query = (
        update(Invitation)
        .where(Invitation.map_id == map_id, Invitation.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    db.execute(query)


def _insert(db, map_id: str, token: str, now: datetime) -> Invitation:
    invitation = Invitation(
        id=str(uuid.uuid4()),
        map_id=map_id,
        token_hash=_hash_token(token),
        created_at=now,
    )
    db.add(invitation)

    return invitation


class InvitationStore:

    @classmethod
    async def generate(cls, map_id: str, user_id: str) -> tuple[Invitation, str]:
        token = _new_token()
        now = datetime.now(timezone.utc)

        with session_scope() as db:
            try:
                owner_id = _lock_owner_of(db, map_id)
            except SQLAlchemyError as error:
                logger.error(f"Fetch map '{map_id}' for invitation failed with: '{error}'")
                raise StoreUnavailable

            if owner_id != user_id:
                raise MapNotFound

            try:
                _revoke_current(db, map_id, now)
                invitation = _insert(db, map_id, token, now)
                db.commit()
                db.refresh(invitation)
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Generate invitation for map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        return invitation, token
