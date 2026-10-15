import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from results.error import ContributorRemoved, InvitationNotFound, NotAuthorized, StoreUnavailable
from store.contributors.store import ContributedMap, ContributorStore, JoinResult
from store.credentials import Credentials
from store.invitations.model import Invitation

_SECRET = "s" * 43
_TOKEN = "token-1"
_AS_CONTRIBUTOR = Credentials(contributor_secret=_SECRET)


def _invitation():
    return Invitation(
        id="inv-1",
        map_id="map-1",
        token_hash="hash",
        created_at=datetime(2026, 10, 16, tzinfo=timezone.utc),
    )


def _scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar_one.return_value = value
    return result


def _row(contributor_id, removed_at=None):
    result = MagicMock()
    result.one.return_value = SimpleNamespace(id=contributor_id, removed_at=removed_at)
    return result


def _db(*results):
    db = MagicMock()
    db.execute.side_effect = list(results)
    return db


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.contributors.store.session_scope", scope)


def _patch_find(**kwargs):
    return patch("store.contributors.store.find_current_invitation", MagicMock(**kwargs))


async def _join(nickname="Ana"):
    return await ContributorStore.join(token=_TOKEN, nickname=nickname, secret=_SECRET)


def _insert_query(db):
    return db.execute.call_args_list[0].args[0]


def _insert_params(db):
    return _insert_query(db).compile(dialect=postgresql.dialect()).params


async def test_join_rejects_an_invitation_that_is_not_current():
    db = _db()

    with _patch_scope(db), _patch_find(return_value=None):
        with pytest.raises(InvitationNotFound):
            await _join()

    db.execute.assert_not_called()
    db.commit.assert_not_called()


async def test_join_looks_the_invitation_up_with_the_token_it_received():
    db = _db(_scalar("c-1"), _scalar("Mapa de prueba"))

    with _patch_scope(db), _patch_find(return_value=_invitation()) as find:
        await _join()

    find.assert_called_once_with(db, _TOKEN)


async def test_join_creates_the_contributor_and_reports_it_as_created():
    db = _db(_scalar("c-1"), _scalar("Mapa de prueba"))

    with _patch_scope(db), _patch_find(return_value=_invitation()):
        result = await _join()

    assert result == JoinResult(contributor_id="c-1", map_id="map-1", map_name="Mapa de prueba", created=True)
    db.commit.assert_called_once()


async def test_join_stores_only_the_hash_of_the_secret():
    db = _db(_scalar("c-1"), _scalar("Mapa de prueba"))

    with _patch_scope(db), _patch_find(return_value=_invitation()):
        await _join()

    params = _insert_params(db)

    assert params["secret_hash"] == hashlib.sha256(_SECRET.encode()).hexdigest()
    assert _SECRET not in params.values()


async def test_join_records_the_invitation_the_contributor_came_through():
    db = _db(_scalar("c-1"), _scalar("Mapa de prueba"))

    with _patch_scope(db), _patch_find(return_value=_invitation()):
        await _join(nickname="Ana")

    params = _insert_params(db)

    assert params["invitation_id"] == "inv-1"
    assert params["map_id"] == "map-1"
    assert params["nickname"] == "Ana"
    assert params["created_at"].tzinfo == timezone.utc


async def test_join_never_overwrites_a_contributor_that_already_exists():
    db = _db(_scalar("c-1"), _scalar("Mapa de prueba"))

    with _patch_scope(db), _patch_find(return_value=_invitation()):
        await _join()

    sql = str(_insert_query(db).compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (map_id, secret_hash) DO NOTHING" in sql


async def test_join_returns_the_existing_contributor_when_it_already_joined():
    db = _db(_scalar(None), _row("c-1"), _scalar("Mapa de prueba"))

    with _patch_scope(db), _patch_find(return_value=_invitation()):
        result = await _join()

    assert result == JoinResult(contributor_id="c-1", map_id="map-1", map_name="Mapa de prueba", created=False)


async def test_join_rejects_a_contributor_that_was_removed():
    removed_at = datetime(2026, 10, 15, tzinfo=timezone.utc)
    db = _db(_scalar(None), _row("c-1", removed_at=removed_at))

    with _patch_scope(db), _patch_find(return_value=_invitation()):
        with pytest.raises(ContributorRemoved):
            await _join()

    db.commit.assert_not_called()


async def test_join_fails_when_the_invitation_cannot_be_fetched():
    db = _db()

    with _patch_scope(db), _patch_find(side_effect=SQLAlchemyError("boom")):
        with pytest.raises(StoreUnavailable):
            await _join()

    db.execute.assert_not_called()


async def test_join_rolls_back_when_the_write_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db), _patch_find(return_value=_invitation()):
        with pytest.raises(StoreUnavailable):
            await _join()

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def _rows(*rows):
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def _maps_query(db):
    return db.execute.call_args.args[0].compile(dialect=postgresql.dialect())


async def test_maps_of_returns_each_map_with_the_nickname_in_the_order_the_query_gives():
    db = _db(_rows(("map-1", "Mapa uno", "Ana"), ("map-2", None, "Anita")))

    with _patch_scope(db):
        maps = await ContributorStore.maps_of(_AS_CONTRIBUTOR)

    assert maps == [
        ContributedMap(map_id="map-1", map_name="Mapa uno", nickname="Ana"),
        ContributedMap(map_id="map-2", map_name=None, nickname="Anita"),
    ]


async def test_maps_of_is_empty_when_the_secret_has_no_active_contributor():
    db = _db(_rows())

    with _patch_scope(db):
        maps = await ContributorStore.maps_of(_AS_CONTRIBUTOR)

    assert maps == []


async def test_maps_of_is_empty_without_a_contributor_credential():
    db = MagicMock()

    with _patch_scope(db):
        maps = await ContributorStore.maps_of(Credentials(user_id="user-1"))

    assert maps == []
    db.execute.assert_not_called()


async def test_maps_of_looks_the_secret_up_by_its_hash():
    db = _db(_rows())

    with _patch_scope(db):
        await ContributorStore.maps_of(_AS_CONTRIBUTOR)

    params = _maps_query(db).params
    assert hashlib.sha256(_SECRET.encode()).hexdigest() in params.values()
    assert _SECRET not in params.values()


async def test_maps_of_leaves_out_removed_contributors():
    db = _db(_rows())

    with _patch_scope(db):
        await ContributorStore.maps_of(_AS_CONTRIBUTOR)

    assert "contributors.removed_at IS NULL" in str(_maps_query(db))


async def test_maps_of_orders_by_when_the_contributor_joined():
    db = _db(_rows())

    with _patch_scope(db):
        await ContributorStore.maps_of(_AS_CONTRIBUTOR)

    assert "ORDER BY contributors.created_at, contributors.id" in str(_maps_query(db))


async def test_maps_of_reports_the_store_unavailable_when_the_query_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await ContributorStore.maps_of(_AS_CONTRIBUTOR)


# ---- active_in ----

async def test_active_in_returns_the_active_contributor_of_the_map():
    contributor = SimpleNamespace(id="c-1", removed_at=None)

    with _patch_scope(_db(_scalar(contributor))):
        assert await ContributorStore.active_in("map-1", _AS_CONTRIBUTOR) is contributor


@pytest.mark.parametrize("contributor", [
    None,
    SimpleNamespace(id="c-1", removed_at=datetime(2026, 10, 1, tzinfo=timezone.utc)),
])
async def test_active_in_rejects_a_secret_without_an_active_contributor(contributor):
    with _patch_scope(_db(_scalar(contributor))):
        with pytest.raises(NotAuthorized):
            await ContributorStore.active_in("map-1", _AS_CONTRIBUTOR)


async def test_active_in_reports_the_store_unavailable_when_the_lookup_fails():
    db = MagicMock()
    db.execute.side_effect = SQLAlchemyError("boom")

    with _patch_scope(db):
        with pytest.raises(StoreUnavailable):
            await ContributorStore.active_in("map-1", _AS_CONTRIBUTOR)
