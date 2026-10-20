from fastapi import APIRouter, HTTPException, Response
from hotosm_auth_fastapi import CurrentUser, CurrentUserOptional

from api.v2.schemas.keys import (
    MAX_KEYS,
    KeyChanges,
    KeyItem,
    KeyValueItem,
    MapKeysResponse,
    MapTagsResponse,
    NewKey,
    PointKeyTags,
    PointTagChange,
    PointTagItem,
)
from results.error import (
    ArchivedValue,
    BuiltinKey,
    InvalidTagValue,
    KeyInUse,
    KeyNameTaken,
    NotAuthorized,
    StoreUnavailable,
    UnknownKey,
    UnknownValue,
    ValueInUse,
)
from store.map_keys_store import MapKeysStore

router = APIRouter()

# What each error of the store means over HTTP
ERRORS = {
    NotAuthorized: (403, "Not authorized."),
    UnknownKey: (404, "Key not found."),
    UnknownValue: (404, "Option not found."),
    BuiltinKey: (409, "A key of the system cannot be removed, renamed nor written here."),
    KeyNameTaken: (409, "The map already has a key with that name."),
    KeyInUse: (409, "A key that was given to points cannot be removed, only archived."),
    ValueInUse: (409, "An option some points have cannot be removed, only archived."),
    ArchivedValue: (409, "The option is archived."),
    StoreUnavailable: (503, "Tags storage unavailable."),
}


async def _call(store_call):
    try:
        return await store_call
    except InvalidTagValue as error:
        raise HTTPException(status_code=422, detail=error.reason)
    except tuple(ERRORS) as error:
        status_code, detail = ERRORS[type(error)]
        raise HTTPException(status_code=status_code, detail=detail)


def _value_item(row) -> KeyValueItem:
    return KeyValueItem(
        id=row.id,
        name=row.value,
        description=row.description or "",
        color=row.color,
        expires_after=int(row.expires_after.total_seconds() // 3600) if row.expires_after else None,
        archived=row.archived_at is not None,
        archived_at=row.archived_at,
    )


def _key_item(key, values) -> KeyItem:
    return KeyItem(
        id=key.id,
        key=key.key,
        single=key.single,
        closed=key.closed,
        builtin=key.builtin,
        colors_map=key.colors_map,
        archived=key.archived_at is not None,
        values=[_value_item(value) for value in values],
    )


def _tag_item(tag) -> PointTagItem:
    return PointTagItem(
        point_id=tag.point_id,
        key_id=tag.key_id,
        value_id=tag.value_id,
        value=tag.value,
        since=tag.since,
        confirmed_at=tag.confirmed_at,
    )


def _values(values) -> list[dict] | None:
    return None if values is None else [value.model_dump(exclude={"archived_at"}) for value in values]


@router.get("/maps/{map_id}/keys")
async def read_keys(map_id: str, user: CurrentUserOptional) -> MapKeysResponse:
    keys = await _call(MapKeysStore.read_keys(map_id, user.id if user else None))
    if keys is None:
        raise HTTPException(status_code=404, detail="Map not found.")
    return MapKeysResponse(keys=[_key_item(key, values) for key, values in keys])


@router.post("/maps/{map_id}/keys", status_code=201)
async def create_key(map_id: str, key: NewKey, user: CurrentUser) -> KeyItem:
    row, values = await _call(MapKeysStore.create_key(
        map_id, user.id, {**key.model_dump(exclude={"values"}), "values": _values(key.values)}, MAX_KEYS,
    ))
    return _key_item(row, values)


@router.put("/maps/{map_id}/keys/{key_id}")
async def update_key(map_id: str, key_id: str, changes: KeyChanges, user: CurrentUser) -> KeyItem:
    row, values = await _call(MapKeysStore.update_key(
        map_id, key_id, user.id,
        {
            "key": changes.key, "archived": changes.archived, "colors_map": changes.colors_map,
            "values": _values(changes.values),
        },
    ))
    return _key_item(row, values)


@router.delete("/maps/{map_id}/keys/{key_id}", status_code=204)
async def remove_key(map_id: str, key_id: str, user: CurrentUser) -> Response:
    await _call(MapKeysStore.remove_key(map_id, key_id, user.id))
    return Response(status_code=204)


@router.get("/maps/{map_id}/tags")
async def read_tags(map_id: str, user: CurrentUserOptional) -> MapTagsResponse:
    tags = await _call(MapKeysStore.read_tags(map_id, user.id if user else None))
    if tags is None:
        raise HTTPException(status_code=404, detail="Map not found.")
    return MapTagsResponse(tags=[_tag_item(tag) for tag in tags])


@router.put("/points/{point_id}/tags/{key_id}")
async def set_point_tag(point_id: str, key_id: str, change: PointTagChange, user: CurrentUser) -> PointKeyTags:
    tags = await _call(MapKeysStore.set_point_tag(
        point_id, key_id, user.id, change.action,
        value_id=change.value_id, value=change.value, happened_at=change.happened_at,
    ))
    return PointKeyTags(tags=[_tag_item(tag) for tag in tags])
