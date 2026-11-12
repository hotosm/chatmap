from fastapi import APIRouter
from hotosm_auth_fastapi import CurrentUser

from api.v2.errors import call_store
from api.v2.schemas.places import PlaceNames
from store.message_suggestions_store import MessageSuggestionsStore
from store.place_names_store import PlaceNamesStore

router = APIRouter()


@router.get("/points/{point_id}/names")
async def read_place_names(point_id: str, user: CurrentUser) -> PlaceNames:
    """The other names of a place: only its owner sees them."""
    return PlaceNames(names=await call_store(PlaceNamesStore.names(point_id, user.id)))


@router.put("/points/{point_id}/names")
async def update_place_names(point_id: str, names: PlaceNames, user: CurrentUser) -> PlaceNames:
    """The other names of a place, instead of the ones it had. The messages nobody answered are read again."""
    map_id, saved = await call_store(PlaceNamesStore.set_names(point_id, user.id, names.names))
    await MessageSuggestionsStore.reread(map_id)
    return PlaceNames(names=saved)
