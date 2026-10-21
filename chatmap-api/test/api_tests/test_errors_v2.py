import pytest
from fastapi import HTTPException

from api.v2.errors import call_store
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


@pytest.mark.parametrize("error, status_code", [
    (NotAuthorized(), 403),
    (UnknownKey("k-9"), 404),
    (UnknownValue("v-9"), 404),
    (KeyNameTaken("Fuel"), 409),
    (KeyInUse("k-1"), 409),
    (ValueInUse(["v-1"]), 409),
    (ArchivedValue("v-1"), 409),
    (TooManyKeys(10), 409),
    (UnknownTagChange(9), 404),
    (InvalidTagValue("a text is needed"), 422),
    (StoreUnavailable(), 503),
])
async def test_store_errors_are_told_over_http(error, status_code):
    async def failing():
        raise error

    with pytest.raises(HTTPException) as raised:
        await call_store(failing())

    assert raised.value.status_code == status_code
