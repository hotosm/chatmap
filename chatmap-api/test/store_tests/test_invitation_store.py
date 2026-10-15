import hashlib
from datetime import timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from results.error import MapNotFound, StoreUnavailable
from store.invitations.model import Invitation
from store.invitations.repository import find_current_invitation
from store.invitations.store import InvitationStore


def _result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _db(owner_id="user-1"):
    db = MagicMock()
    db.execute.side_effect = [_result(owner_id), MagicMock()]
    return db


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.invitations.store.session_scope", scope)


async def _generate(map_id="map-1", user_id="user-1"):
    return await InvitationStore.generate(map_id=map_id, user_id=user_id)


def _sql(query):
    return str(query.compile(dialect=postgresql.dialect()))


def _calls(db):
    return [name for name, *_ in db.method_calls]


async def test_generate_rejects_a_map_that_does_not_exist():
    db = MagicMock()
    db.execute.side_effect = [_result(None)]

    with _patch_scope(db):
        with pytest.raises(MapNotFound):
            await _generate()

    assert db.execute.call_count == 1
    db.add.assert_not_called()
    db.commit.assert_not_called()


async def test_generate_rejects_a_map_of_another_user():
    db = MagicMock()
    db.execute.side_effect = [_result("someone-else")]

    with _patch_scope(db):
        with pytest.raises(MapNotFound):
            await _generate()

    assert db.execute.call_count == 1
    db.add.assert_not_called()
    db.commit.assert_not_called()


async def test_generate_locks_the_map_row_before_touching_invitations():
    db = _db()

    with _patch_scope(db):
        await _generate()

    assert "FOR UPDATE" in _sql(db.execute.call_args_list[0].args[0])


async def test_generate_revokes_the_current_invitation_before_inserting_the_new_one():
    db = _db()

    with _patch_scope(db):
        await _generate()

    revoke = _sql(db.execute.call_args_list[1].args[0])

    assert revoke.startswith("UPDATE invitations SET revoked_at")
    assert "revoked_at IS NULL" in revoke
    assert _calls(db) == ["execute", "execute", "add", "commit", "refresh"]


async def test_generate_stores_only_the_hash_of_the_token():
    db = _db()

    with _patch_scope(db):
        invitation, token = await _generate()

    assert invitation.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert invitation.token_hash != token


async def test_generate_returns_the_invitation_it_added():
    db = _db()

    with _patch_scope(db):
        invitation, _ = await _generate()

    assert db.add.call_args.args[0] is invitation
    assert isinstance(invitation, Invitation)
    assert invitation.map_id == "map-1"
    assert invitation.revoked_at is None
    assert invitation.created_at.tzinfo == timezone.utc


async def test_generate_creates_a_different_token_every_time():
    with _patch_scope(_db()):
        _, first = await _generate()

    with _patch_scope(_db()):
        _, second = await _generate()

    assert first != second


async def test_generate_fails_when_the_map_cannot_be_fetched():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _generate()

    db.add.assert_not_called()


async def test_generate_rolls_back_when_the_write_fails():
    db = MagicMock()
    db.execute.side_effect = [_result("user-1"), SQLAlchemyError("boom")]

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await _generate()

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_find_current_invitation_matches_the_hash_of_the_token_among_the_current_ones():
    db = MagicMock()
    db.execute.return_value = _result("invitation")

    found = find_current_invitation(db, "token-1")

    query = db.execute.call_args.args[0]
    query_params = query.compile(dialect=postgresql.dialect()).params

    assert found == "invitation"
    assert "revoked_at IS NULL" in _sql(query)
    assert hashlib.sha256(b"token-1").hexdigest() in query_params.values()
    assert "token-1" not in query_params.values()
