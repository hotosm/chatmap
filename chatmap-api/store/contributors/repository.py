import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from db import Map
from store.contributors.model import Contributor, hash_secret
from store.credentials import Credentials


def contributor_match(credentials: Credentials):
    if credentials.contributor_secret is not None:
        return Contributor.secret_hash == hash_secret(credentials.contributor_secret)

    # A logged-in contributor will match by user_id here
    return None


def find_contributor(db, map_id: str, credentials: Credentials) -> Contributor | None:
    match = contributor_match(credentials)

    if match is None:
        return None

    query = select(Contributor).where(Contributor.map_id == map_id, match)

    return db.execute(query).scalar_one_or_none()


def insert_if_new(db, map_id: str, invitation_id: str, secret_hash: str, nickname: str, now: datetime) -> str | None:
    query = (
        insert(Contributor)
        .values(
            id=str(uuid.uuid4()),
            map_id=map_id,
            invitation_id=invitation_id,
            secret_hash=secret_hash,
            nickname=nickname,
            created_at=now,
        )
        .on_conflict_do_nothing(index_elements=["map_id", "secret_hash"])
        .returning(Contributor.id)
    )

    return db.execute(query).scalar_one_or_none()


def find_existing(db, map_id: str, secret_hash: str):
    query = select(Contributor.id, Contributor.removed_at).where(
        Contributor.map_id == map_id,
        Contributor.secret_hash == secret_hash,
    )

    return db.execute(query).one()


def map_name_of(db, map_id: str) -> str:
    return db.execute(select(Map.name).where(Map.id == map_id)).scalar_one()


def contributed_maps(db, credentials: Credentials):
    match = contributor_match(credentials)

    if match is None:
        return []

    query = (
        select(Map.id, Map.name, Contributor.nickname)
        .select_from(Contributor)
        .join(Map, Map.id == Contributor.map_id)
        .where(match, Contributor.removed_at.is_(None))
        .order_by(Contributor.created_at, Contributor.id)
    )

    return db.execute(query).all()
