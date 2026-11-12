import hashlib
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint

from db import Base, Point


class Contributor(Base):
    __tablename__ = "contributors"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    map_id = Column(String, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    invitation_id = Column(String, ForeignKey("invitations.id", ondelete="CASCADE"), nullable=False)
    secret_hash = Column(String, nullable=True)
    nickname = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    removed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("map_id", "secret_hash", name="uq_contributors_map_id_secret_hash"),
        Index("ix_contributors_invitation_id_created_at", "invitation_id", "created_at"),
        Index("ix_contributors_secret_hash", "secret_hash"),
    )


Point.__table__.append_constraint(
    ForeignKeyConstraint(["contributor_id"], ["contributors.id"], name="fk_points_contributor_id_contributors")
)


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()
