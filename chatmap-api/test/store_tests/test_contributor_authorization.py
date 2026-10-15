import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from results.error import MapNotFound, NotAuthorized
from store.contributors.authorization import Owner, active_contributor, role_in_map
from store.credentials import Credentials

_SECRET = "s" * 43
_AS_CONTRIBUTOR = Credentials(contributor_secret=_SECRET)


def _contributor(contributor_id="c-1", removed_at=None):
    return SimpleNamespace(id=contributor_id, removed_at=removed_at)


def _db(contributor=None):
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = contributor
    return db


# ---- active_contributor ----

def test_active_contributor_is_none_without_a_contributor_secret():
    db = _db(_contributor())

    assert active_contributor(db, "map-1", Credentials(user_id="user-1")) is None
    db.execute.assert_not_called()


def test_active_contributor_returns_the_contributor_of_the_secret():
    contributor = _contributor()

    assert active_contributor(_db(contributor), "map-1", _AS_CONTRIBUTOR) is contributor


def test_active_contributor_is_none_when_the_secret_is_not_a_contributor_of_the_map():
    assert active_contributor(_db(None), "map-1", _AS_CONTRIBUTOR) is None


def test_active_contributor_is_none_for_a_removed_contributor():
    removed = _contributor(removed_at=datetime(2026, 10, 1, tzinfo=timezone.utc))

    assert active_contributor(_db(removed), "map-1", _AS_CONTRIBUTOR) is None


def test_active_contributor_looks_the_secret_up_by_its_hash_in_the_map():
    db = _db(_contributor())

    active_contributor(db, "map-1", _AS_CONTRIBUTOR)

    params = db.execute.call_args.args[0].compile(dialect=postgresql.dialect()).params
    assert "map-1" in params.values()
    assert hashlib.sha256(_SECRET.encode()).hexdigest() in params.values()
    assert _SECRET not in params.values()


# ---- role_in_map ----

def test_the_owner_of_the_map_is_the_owner():
    db = _db()
    credentials = Credentials(user_id="user-1", username="joaco")

    assert role_in_map(db, "map-1", "user-1", credentials) == Owner(user_id="user-1", username="joaco")
    db.execute.assert_not_called()


def test_a_session_of_another_user_does_not_learn_that_the_map_exists():
    db = _db()

    with pytest.raises(MapNotFound):
        role_in_map(db, "map-1", "someone-else", Credentials(user_id="user-1"))

    db.execute.assert_not_called()


def test_no_credentials_have_no_role():
    with pytest.raises(MapNotFound):
        role_in_map(_db(), "map-1", "user-1", Credentials())


def test_an_active_contributor_is_that_contributor():
    contributor = _contributor()

    assert role_in_map(_db(contributor), "map-1", "owner-1", _AS_CONTRIBUTOR) is contributor


def test_a_secret_that_is_not_a_contributor_of_the_map_is_not_authorized():
    with pytest.raises(NotAuthorized):
        role_in_map(_db(None), "map-1", "owner-1", _AS_CONTRIBUTOR)


def test_a_removed_contributor_is_not_authorized():
    removed = _contributor(removed_at=datetime(2026, 10, 1, tzinfo=timezone.utc))

    with pytest.raises(NotAuthorized):
        role_in_map(_db(removed), "map-1", "owner-1", _AS_CONTRIBUTOR)
