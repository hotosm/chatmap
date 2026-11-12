import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from db import session_scope
from results.error import ContributorRemoved, InvitationNotFound, NotAuthorized, StoreUnavailable
from store.contributors.authorization import active_contributor
from store.contributors.model import Contributor, hash_secret
from store.contributors.repository import contributed_maps, find_existing, insert_if_new, map_name_of
from store.credentials import Credentials
from store.invitations.repository import find_current_invitation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JoinResult:
    contributor_id: str
    map_id: str
    map_name: str
    created: bool


@dataclass(frozen=True)
class ContributedMap:
    map_id: str
    map_name: str | None
    nickname: str


class ContributorStore:

    @classmethod
    async def join(cls, token: str, nickname: str, secret: str) -> JoinResult:
        secret_hash = hash_secret(secret)
        now = datetime.now(timezone.utc)

        with session_scope() as db:
            try:
                invitation = find_current_invitation(db, token)
            except SQLAlchemyError as error:
                logger.error(f"Fetch invitation to join failed with: '{error}'")
                raise StoreUnavailable

            if invitation is None:
                raise InvitationNotFound

            map_id = invitation.map_id
            invitation_id = invitation.id

            try:
                contributor_id = insert_if_new(db, map_id, invitation_id, secret_hash, nickname, now)
                created = contributor_id is not None

                if not created:
                    existing = find_existing(db, map_id, secret_hash)

                    if existing.removed_at is not None:
                        raise ContributorRemoved

                    contributor_id = existing.id

                map_name = map_name_of(db, map_id)
                db.commit()
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Join map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        return JoinResult(contributor_id=contributor_id, map_id=map_id, map_name=map_name, created=created)

    @classmethod
    async def active_in(cls, map_id: str, credentials: Credentials) -> Contributor:
        with session_scope() as db:
            try:
                contributor = active_contributor(db, map_id, credentials)
            except SQLAlchemyError as error:
                logger.error(f"Fetch the contributor of map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        if contributor is None:
            raise NotAuthorized

        return contributor

    @classmethod
    async def maps_of(cls, credentials: Credentials) -> list[ContributedMap]:
        with session_scope() as db:
            try:
                rows = contributed_maps(db, credentials)
            except SQLAlchemyError as error:
                logger.error(f"Fetch the maps of a contributor failed with: '{error}'")
                raise StoreUnavailable

        return [ContributedMap(map_id=row[0], map_name=row[1], nickname=row[2]) for row in rows]
