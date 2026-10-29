import hashlib
import secrets
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, text

from db import Base


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


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
