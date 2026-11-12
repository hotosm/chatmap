from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from api.v2.routes.contributors import join_invitation
from api.v2.schemas.contributor import JoinRequest
from results.error import ContributorRemoved, InvitationNotFound, StoreUnavailable
from store.contributors.store import JoinResult

_SECRET = "a" * 43


def _body(**overrides):
    return {"token": "token-1", "nickname": "Ana", "secret": _SECRET, **overrides}


def _request(**overrides):
    return JoinRequest.model_validate(_body(**overrides))


def _result(created=True):
    return JoinResult(contributor_id="c-1", map_id="map-1", map_name="Mapa de prueba", created=created)


def _patch_store(**kwargs):
    return patch("api.v2.routes.contributors.ContributorStore.join", AsyncMock(**kwargs))


# ---- POST /v2/invitations/join ----

async def test_join_answers_created_with_the_contributor_and_the_map():
    response = Response()

    with _patch_store(return_value=_result(created=True)):
        result = await join_invitation(join=_request(), response=response)

    assert response.status_code == 201
    assert result.contributor_id == "c-1"
    assert result.map_id == "map-1"
    assert result.map_name == "Mapa de prueba"


async def test_join_answers_ok_when_the_person_was_already_a_contributor():
    response = Response()

    with _patch_store(return_value=_result(created=False)):
        result = await join_invitation(join=_request(), response=response)

    assert response.status_code == 200
    assert result.contributor_id == "c-1"


async def test_join_asks_the_store_with_the_token_the_nickname_and_the_secret():
    with _patch_store(return_value=_result()) as store:
        await join_invitation(join=_request(), response=Response())

    store.assert_awaited_once_with("token-1", "Ana", _SECRET)


async def test_join_answers_not_found_for_an_invitation_that_is_not_current():
    with _patch_store(side_effect=InvitationNotFound):
        with pytest.raises(HTTPException) as error:
            await join_invitation(join=_request(), response=Response())

    assert error.value.status_code == 404


async def test_join_answers_forbidden_for_a_removed_contributor():
    with _patch_store(side_effect=ContributorRemoved):
        with pytest.raises(HTTPException) as error:
            await join_invitation(join=_request(), response=Response())

    assert error.value.status_code == 403


async def test_join_answers_unavailable_when_the_store_is_down():
    with _patch_store(side_effect=StoreUnavailable):
        with pytest.raises(HTTPException) as error:
            await join_invitation(join=_request(), response=Response())

    assert error.value.status_code == 503


# ---- request validation ----

def test_the_secret_accepts_32_bytes_written_as_base64url():
    assert _request(secret="A" * 21 + "_-" + "9" * 20).secret


@pytest.mark.parametrize("secret", [
    "",
    "a" * 42,
    "a" * 44,
    "a" * 42 + "+",
    "a" * 42 + "=",
    "a" * 42 + " ",
    "a" * 43 + "\n",
])
def test_the_secret_rejects_anything_that_is_not_43_base64url_characters(secret):
    with pytest.raises(ValidationError):
        _request(secret=secret)


@pytest.mark.parametrize("nickname", ["", "   "])
def test_the_nickname_cannot_be_blank(nickname):
    with pytest.raises(ValidationError):
        _request(nickname=nickname)


def test_the_nickname_is_trimmed():
    assert _request(nickname="  Ana ").nickname == "Ana"


def test_the_token_cannot_be_empty():
    with pytest.raises(ValidationError):
        _request(token="")
