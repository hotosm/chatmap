from fastapi import APIRouter, Depends, HTTPException

from api.v2.credentials import RequestCredentials, require_credential
from api.v2.schemas.map import MapResponse, MapsResponse
from results.error import StoreUnavailable
from store.contributors.store import ContributorStore
from store.credentials import Credentials
from store.maps.store import MapStore

router = APIRouter()


async def _contributor_maps(credentials: Credentials) -> list[MapResponse]:
    maps = await ContributorStore.maps_of(credentials)

    return [
        MapResponse(map_id=item.map_id, map_name=item.map_name, role="contributor", nickname=item.nickname)
        for item in maps
    ]


async def _owner_maps(user_id: str) -> list[MapResponse]:
    maps = await MapStore.owned_by(user_id)

    return [MapResponse(map_id=item.map_id, map_name=item.map_name, role="owner", nickname=None) for item in maps]


@router.get("/maps", dependencies=[Depends(require_credential)])
async def list_maps(credentials: RequestCredentials) -> MapsResponse:
    try:
        if credentials.contributor_secret is not None:
            maps = await _contributor_maps(credentials)
        elif credentials.user_id is not None:
            maps = await _owner_maps(credentials.user_id)
        else:
            raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Map storage unavailable.")

    return MapsResponse(maps=maps)
