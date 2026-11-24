from fastapi import APIRouter
from hotosm_auth_fastapi import CurrentUser

from api.v2.errors import call_store
from api.v2.schemas.places import NamedPlace, PlaceName, PlaceNames
from store.message_suggestions_store import MessageSuggestionsStore
from store.place_names_store import PlaceNamesStore
from store.points.store import PointStore

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


@router.put("/points/{point_id}/name")
async def update_place_name(point_id: str, place: PlaceName, user: CurrentUser) -> NamedPlace:
    """
    The name of a place, or of a report sent from the field, which makes it a
    place. The messages nobody answered are read again: the name says the place.
    """
    map_id, was_report = await call_store(PointStore.name_point(point_id, user.id, place.name))
    await MessageSuggestionsStore.reread(map_id)
    return NamedPlace(id=point_id, name=place.name, was_report=was_report)
