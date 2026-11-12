import uuid
from datetime import datetime

from sqlalchemy import select, update

from db import Map
from store.invitations.model import Invitation, hash_token


def lock_owner_of(db, map_id: str) -> str | None:
    query = select(Map.owner_id).where(Map.id == map_id).with_for_update()

    return db.execute(query).scalar_one_or_none()


def revoke_current(db, map_id: str, now: datetime) -> None:
    query = (
        update(Invitation)
        .where(Invitation.map_id == map_id, Invitation.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    db.execute(query)


def find_current_invitation(db, token: str) -> Invitation | None:
    query = select(Invitation).where(
        Invitation.token_hash == hash_token(token),
        Invitation.revoked_at.is_(None),
    )

    return db.execute(query).scalar_one_or_none()


def insert(db, map_id: str, token: str, now: datetime) -> Invitation:
    invitation = Invitation(
        id=str(uuid.uuid4()),
        map_id=map_id,
        token_hash=hash_token(token),
        created_at=now,
    )
    db.add(invitation)

    return invitation
