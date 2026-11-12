from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.v2.credentials import contributor_secret, request_credentials, require_credential
from store.credentials import Credentials

_SECRET = "A" * 43


def test_no_authorization_header_means_no_contributor():
    assert contributor_secret(None) is None


def test_a_bearer_token_is_not_a_contributor_credential():
    assert contributor_secret("Bearer some.jwt.token") is None


def test_a_contributor_credential_returns_the_secret():
    assert contributor_secret(f"Contributor {_SECRET}") == _SECRET


def test_the_scheme_is_case_insensitive():
    assert contributor_secret(f"contributor {_SECRET}") == _SECRET


@pytest.mark.parametrize("header", [
    "Contributor",
    "Contributor ",
    f"Contributor {'A' * 42}",
    f"Contributor {'A' * 44}",
    f"Contributor {'A' * 42}+",
    f"Contributor {_SECRET} extra",
])
def test_a_malformed_secret_is_rejected(header):
    with pytest.raises(HTTPException) as raised:
        contributor_secret(header)

    assert raised.value.status_code == 401


def test_a_request_with_neither_session_nor_secret_is_unauthorized():
    with pytest.raises(HTTPException) as raised:
        require_credential(user=None, secret=None)

    assert raised.value.status_code == 401
    assert raised.value.headers == {"WWW-Authenticate": "Bearer"}


def test_a_request_with_a_session_is_authenticated():
    assert require_credential(user=object(), secret=None) is None


def test_a_request_with_a_secret_is_authenticated():
    assert require_credential(user=None, secret=_SECRET) is None


def test_the_credentials_of_a_session_carry_the_user_id_and_username():
    user = SimpleNamespace(id="user-1", username="joaco")

    assert request_credentials(user=user, secret=None) == Credentials(user_id="user-1", username="joaco")


def test_the_credentials_of_a_session_without_username_carry_no_username():
    user = SimpleNamespace(id="user-1", username=None)

    assert request_credentials(user=user, secret=None) == Credentials(user_id="user-1")


def test_the_credentials_of_a_contributor_carry_the_secret():
    assert request_credentials(user=None, secret=_SECRET) == Credentials(contributor_secret=_SECRET)


def test_with_both_credentials_only_the_secret_is_kept():
    user = SimpleNamespace(id="user-1", username="joaco")

    assert request_credentials(user=user, secret=_SECRET) == Credentials(contributor_secret=_SECRET)
