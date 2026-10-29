from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from hotosm_auth_fastapi import get_current_user_optional

from api.v2 import router as v2_router
from api.v2.routes.maps import list_maps
from results.error import StoreUnavailable
from store.contributors.store import ContributedMap
from store.credentials import Credentials
from store.maps.store import OwnedMap

_SECRET = "A" * 43
_USER = SimpleNamespace(id="user-1", username="joaco")
_OWNER = Credentials(user_id="user-1", username="joaco")
_AS_CONTRIBUTOR = Credentials(contributor_secret=_SECRET)


def _patch_contributor_store(**kwargs):
    return patch("api.v2.routes.maps.ContributorStore.maps_of", AsyncMock(**kwargs))


def _patch_owner_store(**kwargs):
    return patch("api.v2.routes.maps.MapStore.owned_by", AsyncMock(**kwargs))


def _client(user=None):
    app = FastAPI()
    app.include_router(v2_router)
    app.dependency_overrides[get_current_user_optional] = lambda: user
    return TestClient(app)


# ---- GET /v2/maps ----

async def test_list_with_a_secret_returns_each_joined_map_as_contributor_with_its_nickname():
    maps = [
        ContributedMap(map_id="map-1", map_name="Mapa uno", nickname="Ana"),
        ContributedMap(map_id="map-2", map_name=None, nickname="Anita"),
    ]

    with _patch_contributor_store(return_value=maps):
        result = await list_maps(credentials=_AS_CONTRIBUTOR)

    assert result.model_dump() == {
        "maps": [
            {"map_id": "map-1", "map_name": "Mapa uno", "role": "contributor", "nickname": "Ana"},
            {"map_id": "map-2", "map_name": None, "role": "contributor", "nickname": "Anita"},
        ],
    }


async def test_list_with_a_session_returns_each_owned_map_as_owner_without_nickname():
    maps = [
        OwnedMap(map_id="map-1", map_name="Mapa uno"),
        OwnedMap(map_id="map-2", map_name=None),
    ]

    with _patch_owner_store(return_value=maps):
        result = await list_maps(credentials=_OWNER)

    assert result.model_dump() == {
        "maps": [
            {"map_id": "map-1", "map_name": "Mapa uno", "role": "owner", "nickname": None},
            {"map_id": "map-2", "map_name": None, "role": "owner", "nickname": None},
        ],
    }


async def test_list_asks_the_owner_store_with_the_user_id():
    with _patch_owner_store(return_value=[]) as store:
        await list_maps(credentials=_OWNER)

    store.assert_awaited_once_with("user-1")


async def test_list_without_credentials_answers_unauthorized():
    with _patch_contributor_store(return_value=[]) as contributor_store, \
            _patch_owner_store(return_value=[]) as owner_store:
        with pytest.raises(HTTPException) as raised:
            await list_maps(credentials=Credentials())

    assert raised.value.status_code == 401
    contributor_store.assert_not_awaited()
    owner_store.assert_not_awaited()


async def test_list_is_empty_when_the_contributor_has_no_maps():
    with _patch_contributor_store(return_value=[]):
        result = await list_maps(credentials=_AS_CONTRIBUTOR)

    assert result.maps == []


async def test_list_answers_unavailable_when_the_contributor_store_fails():
    with _patch_contributor_store(side_effect=StoreUnavailable()):
        with pytest.raises(HTTPException) as raised:
            await list_maps(credentials=_AS_CONTRIBUTOR)

    assert raised.value.status_code == 503


async def test_list_answers_unavailable_when_the_owner_store_fails():
    with _patch_owner_store(side_effect=StoreUnavailable()):
        with pytest.raises(HTTPException) as raised:
            await list_maps(credentials=_OWNER)

    assert raised.value.status_code == 503


# ---- GET /v2/maps over HTTP ----

def test_http_with_a_contributor_secret_lists_the_joined_maps():
    maps = [ContributedMap(map_id="map-1", map_name="Mapa uno", nickname="Ana")]

    with _patch_contributor_store(return_value=maps) as store:
        response = _client().get("/v2/maps", headers={"Authorization": f"Contributor {_SECRET}"})

    assert response.status_code == 200
    assert response.json() == {
        "maps": [{"map_id": "map-1", "map_name": "Mapa uno", "role": "contributor", "nickname": "Ana"}],
    }
    store.assert_awaited_once_with(_AS_CONTRIBUTOR)


def test_http_with_only_a_session_lists_the_owned_maps():
    maps = [OwnedMap(map_id="map-1", map_name="Mapa uno")]

    with _patch_owner_store(return_value=maps) as store:
        response = _client(user=_USER).get("/v2/maps")

    assert response.status_code == 200
    assert response.json() == {
        "maps": [{"map_id": "map-1", "map_name": "Mapa uno", "role": "owner", "nickname": None}],
    }
    store.assert_awaited_once_with("user-1")


def test_http_with_a_session_and_a_secret_lists_the_joined_maps():
    with _patch_contributor_store(return_value=[]) as contributor_store, \
            _patch_owner_store(return_value=[]) as owner_store:
        response = _client(user=_USER).get("/v2/maps", headers={"Authorization": f"Contributor {_SECRET}"})

    assert response.status_code == 200
    contributor_store.assert_awaited_once_with(_AS_CONTRIBUTOR)
    owner_store.assert_not_awaited()


def test_http_without_credentials_answers_unauthorized():
    response = _client().get("/v2/maps")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_http_with_a_malformed_secret_answers_unauthorized():
    response = _client().get("/v2/maps", headers={"Authorization": "Contributor nope"})

    assert response.status_code == 401
