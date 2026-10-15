import logging
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError

from db import session_scope
from results.error import MapNotFound, StoreUnavailable
from store.contributors.authorization import Owner, role_in_map
from store.contributors.model import Contributor
from store.credentials import Credentials
from store.maps.repository import owned_maps, owner_of

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OwnedMap:
    map_id: str
    map_name: str | None


class MapStore:

    @classmethod
    async def owned_by(cls, user_id: str) -> list[OwnedMap]:
        with session_scope() as db:
            try:
                rows = owned_maps(db, user_id)
            except SQLAlchemyError as error:
                logger.error(f"Fetch the maps of owner '{user_id}' failed with: '{error}'")
                raise StoreUnavailable

        return [OwnedMap(map_id=row[0], map_name=row[1]) for row in rows]

    @classmethod
    async def role_of(cls, map_id: str, credentials: Credentials) -> Owner | Contributor:
        with session_scope() as db:
            try:
                owner_id = owner_of(db, map_id)

                if owner_id is None:
                    raise MapNotFound

                return role_in_map(db, map_id, owner_id, credentials)
            except SQLAlchemyError as error:
                logger.error(f"Fetch the role in map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable
