import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from db import session_scope
from results.error import MapNotFound, StoreUnavailable
from store.invitations.model import Invitation, new_token
from store.invitations.repository import insert, lock_owner_of, revoke_current

logger = logging.getLogger(__name__)


class InvitationStore:

    @classmethod
    async def generate(cls, map_id: str, user_id: str) -> tuple[Invitation, str]:
        token = new_token()
        now = datetime.now(timezone.utc)

        with session_scope() as db:
            try:
                owner_id = lock_owner_of(db, map_id)
            except SQLAlchemyError as error:
                logger.error(f"Fetch map '{map_id}' for invitation failed with: '{error}'")
                raise StoreUnavailable

            if owner_id != user_id:
                raise MapNotFound

            try:
                revoke_current(db, map_id, now)
                invitation = insert(db, map_id, token, now)
                db.commit()
                db.refresh(invitation)
            except SQLAlchemyError as error:
                db.rollback()
                logger.error(f"Generate invitation for map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable

        return invitation, token
