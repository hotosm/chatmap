from fastapi import HTTPException

from results.error import (
    ArchivedValue,
    InvalidTagValue,
    KeyInUse,
    KeyNameTaken,
    NotAuthorized,
    StoreUnavailable,
    TooManyKeys,
    UnknownKey,
    UnknownTagChange,
    UnknownValue,
    ValueInUse,
)

# What each error of the tag stores means over HTTP
ERRORS = {
    NotAuthorized: (403, "Not authorized."),
    UnknownKey: (404, "Key not found."),
    UnknownValue: (404, "Value not found."),
    UnknownTagChange: (404, "Change not found."),
    KeyNameTaken: (409, "The map already has a key with that name."),
    KeyInUse: (409, "A key that was given to points cannot be removed, only archived."),
    ValueInUse: (409, "A value some points have cannot be removed, only archived."),
    ArchivedValue: (409, "The value is archived."),
    TooManyKeys: (409, "The map has as many keys as it can take."),
    StoreUnavailable: (503, "Tags storage unavailable."),
}


async def call_store(store_call):
    """Await a call to a tag store, telling its errors over HTTP."""
    try:
        return await store_call
    except InvalidTagValue as error:
        raise HTTPException(status_code=422, detail=error.reason)
    except tuple(ERRORS) as error:
        status_code, detail = ERRORS[type(error)]
        raise HTTPException(status_code=status_code, detail=detail)
