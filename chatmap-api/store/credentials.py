from dataclasses import dataclass


@dataclass(frozen=True)
class Credentials:
    user_id: str | None = None
    username: str | None = None
    contributor_secret: str | None = None
