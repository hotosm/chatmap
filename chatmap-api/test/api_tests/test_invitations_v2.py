from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.v2.routes.invitations import generate_invitation
from results.error import MapNotFound, StoreUnavailable
from store.invitation_store import Invitation

_CREATED_AT = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _invitation():
    return Invitation(id="inv-1", map_id="map-1", token_hash="hash", created_at=_CREATED_AT)


def _patch_store(**kwargs):
    return patch("api.v2.routes.invitations.InvitationStore.generate", AsyncMock(**kwargs))


# ---- POST /v2/maps/{map_id}/invitations ----

async def test_generate_returns_the_invitation_with_its_token_and_link():
    with _patch_store(return_value=(_invitation(), "token-1")):
        result = await generate_invitation(map_id="map-1", user=_user())

    assert result.id == "inv-1"
    assert result.token == "token-1"
    assert result.url == "hot-chatmap://join?token=token-1"
    assert result.created_at == _CREATED_AT


async def test_generate_asks_the_store_with_the_map_and_the_user():
    with _patch_store(return_value=(_invitation(), "token-1")) as store:
        await generate_invitation(map_id="map-1", user=_user("user-7"))

    store.assert_awaited_once_with("map-1", "user-7")


async def test_generate_answers_not_found_for_a_missing_or_foreign_map():
    with _patch_store(side_effect=MapNotFound):
        with pytest.raises(HTTPException) as error:
            await generate_invitation(map_id="map-1", user=_user())

    assert error.value.status_code == 404


async def test_generate_answers_unavailable_when_the_store_is_down():
    with _patch_store(side_effect=StoreUnavailable):
        with pytest.raises(HTTPException) as error:
            await generate_invitation(map_id="map-1", user=_user())

    assert error.value.status_code == 503
