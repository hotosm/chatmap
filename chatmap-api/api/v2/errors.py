from fastapi import HTTPException

from results.error import (
    ArchivedValue,
    InvalidTagValue,
    KeyInUse,
    KeyNameTaken,
    MapNotFound,
    MapNotLive,
    NotAuthorized,
    StoreUnavailable,
    TooManyKeys,
    UnknownGroup,
    UnknownKey,
    UnknownTagChange,
    UnknownValue,
    ValueInUse,
)

# What each error of the tag and message stores means over HTTP
ERRORS = {
    NotAuthorized: (403, "Not authorized."),
    MapNotFound: (404, "Map not found."),
    UnknownGroup: (404, "Chat group not found."),
    MapNotLive: (409, "Only a live map listens to chat groups."),
    UnknownKey: (404, "Key not found."),
    UnknownValue: (404, "Value not found."),
    UnknownTagChange: (404, "Change not found."),
    KeyNameTaken: (409, "The map already has a key with that name."),
    KeyInUse: (409, "A key that was given to points cannot be removed, only archived."),
    ValueInUse: (409, "A value some points have cannot be removed, only archived."),
    ArchivedValue: (409, "The value is archived."),
    TooManyKeys: (409, "The map has as many keys as it can take."),
    StoreUnavailable: (503, "Storage unavailable."),
}


async def call_store(store_call):
    """Await a call to a tag or message store, telling its errors over HTTP."""
    try:
        return await store_call
    except InvalidTagValue as error:
        raise HTTPException(status_code=422, detail=error.reason)
    except tuple(ERRORS) as error:
        status_code, detail = ERRORS[type(error)]
        raise HTTPException(status_code=status_code, detail=detail)
