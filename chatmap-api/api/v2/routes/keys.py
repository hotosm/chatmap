from fastapi import APIRouter, HTTPException, Response
from hotosm_auth_fastapi import CurrentUser, CurrentUserOptional

from api.v2.errors import call_store
from api.v2.schemas.keys import MAX_KEYS, KeyChanges, KeyItem, KeyValueItem, MapKeysResponse, NewKey
from settings import ENABLE_GROUP_MESSAGES
from store.map_keys_store import MapKeysStore
from store.message_suggestions_store import MessageSuggestionsStore

router = APIRouter()


async def _read_messages_again(map_id: str, when: bool = True) -> None:
    """
    The words of the values of a map say what its messages suggest: the ones
    nobody answered are read again, when a change may say otherwise (not a
    name or a color).
    """
    if ENABLE_GROUP_MESSAGES and when:
        await MessageSuggestionsStore.reread(map_id)


def _value_item(row) -> KeyValueItem:
    return KeyValueItem(
        id=row.id,
        value=row.value,
        description=row.description or "",
        color=row.color,
        expires_after=int(row.expires_after.total_seconds() // 3600) if row.expires_after else None,
        archived=row.archived_at is not None,
        words=list(row.words or []),
    )


def _key_item(key, values) -> KeyItem:
    return KeyItem(
        id=key.id,
        key=key.key,
        single=key.single,
        closed=key.closed,
        colors_map=key.colors_map,
        archived=key.archived_at is not None,
        values=[_value_item(value) for value in values],
    )


@router.get("/maps/{map_id}/keys")
async def read_keys(map_id: str, user: CurrentUserOptional) -> MapKeysResponse:
    keys = await call_store(MapKeysStore.read_keys(map_id, user.id if user else None))
    if keys is None:
        raise HTTPException(status_code=404, detail="Map not found.")
    return MapKeysResponse(keys=[_key_item(key, values) for key, values in keys])


@router.post("/maps/{map_id}/keys", status_code=201)
async def create_key(map_id: str, key: NewKey, user: CurrentUser) -> KeyItem:
    row, values = await call_store(MapKeysStore.create_key(map_id, user.id, key.model_dump(), MAX_KEYS))
    await _read_messages_again(map_id, any(value.words for value in values))
    return _key_item(row, values)


@router.put("/maps/{map_id}/keys/{key_id}")
async def update_key(map_id: str, key_id: str, changes: KeyChanges, user: CurrentUser) -> KeyItem:
    row, values = await call_store(MapKeysStore.update_key(map_id, key_id, user.id, changes.model_dump()))
    await _read_messages_again(map_id, changes.values is not None or changes.archived is not None)
    return _key_item(row, values)


@router.delete("/maps/{map_id}/keys/{key_id}", status_code=204)
async def remove_key(map_id: str, key_id: str, user: CurrentUser) -> Response:
    await call_store(MapKeysStore.remove_key(map_id, key_id, user.id))
    await _read_messages_again(map_id)
    return Response(status_code=204)
