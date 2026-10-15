from dataclasses import dataclass

from results.error import MapNotFound, NotAuthorized
from store.contributors.model import Contributor
from store.contributors.repository import find_contributor
from store.credentials import Credentials


@dataclass(frozen=True)
class Owner:
    user_id: str
    username: str | None


def active_contributor(db, map_id: str, credentials: Credentials) -> Contributor | None:
    contributor = find_contributor(db, map_id, credentials)

    return contributor if contributor is not None and contributor.removed_at is None else None


def role_in_map(db, map_id: str, owner_id: str, credentials: Credentials) -> Owner | Contributor:
    if credentials.user_id is not None and credentials.user_id == owner_id:
        return Owner(user_id=credentials.user_id, username=credentials.username)

    contributor = active_contributor(db, map_id, credentials)

    if contributor is not None:
        return contributor

    # A session gets 404 for a map that is not theirs, as v1 does; a contributor gets 403
    raise NotAuthorized if credentials.contributor_secret is not None else MapNotFound
