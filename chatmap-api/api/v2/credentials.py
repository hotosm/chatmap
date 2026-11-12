import re
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from hotosm_auth_fastapi import CurrentUserOptional

from api.v2.schemas.contributor import SECRET_PATTERN
from store.credentials import Credentials

CONTRIBUTOR_SCHEME = "contributor"


def contributor_secret(authorization: Annotated[str | None, Header()] = None) -> str | None:
    if authorization is None:
        return None

    scheme, _, secret = authorization.partition(" ")

    if scheme.lower() != CONTRIBUTOR_SCHEME:
        return None

    if not re.fullmatch(SECRET_PATTERN, secret):
        raise HTTPException(status_code=401, detail="Invalid contributor credentials.")

    return secret


ContributorSecret = Annotated[str | None, Depends(contributor_secret)]


def require_contributor_secret(secret: ContributorSecret) -> str:
    if secret is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Contributor"})

    return secret


def require_credential(user: CurrentUserOptional, secret: ContributorSecret) -> None:
    if user is None and secret is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})


def request_credentials(user: CurrentUserOptional, secret: ContributorSecret) -> Credentials:
    # With both credentials, the contributor secret wins
    if secret is not None:
        return Credentials(contributor_secret=secret)

    return Credentials(user_id=user.id if user else None, username=user.username if user else None)


RequestCredentials = Annotated[Credentials, Depends(request_credentials)]
