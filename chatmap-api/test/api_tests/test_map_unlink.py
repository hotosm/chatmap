import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

# main.py wires up hotosm_auth_fastapi at import time, which requires these to
# be set even though these tests never talk to Hanko.
os.environ.setdefault("HANKO_API_URL", "http://localhost:8002")
os.environ.setdefault("COOKIE_SECRET", "dev-secret-key-min-32-bytes-long!")

from db import Map
from main import unlink_map


def _map(owner_id="user-1"):
    return Map(id="map-1", owner_id=owner_id, is_live=True, bot_active=True)


def _db(map_obj):
    db = MagicMock(spec=Session)
    db.get.return_value = map_obj
    return db


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


async def test_unlink_clears_is_live_and_bot_active():
    map_obj = _map()
    db = _db(map_obj)

    with patch("main.clean_user_stream", AsyncMock()) as clean:
        result = await unlink_map(map_id="map-1", user=_user(), db=db)

    assert map_obj.is_live is False
    assert map_obj.bot_active is False
    db.commit.assert_called_once()
    clean.assert_awaited_once_with("user-1")
    assert result == {"is_live": False}


async def test_unlink_rejects_a_non_owner():
    map_obj = _map(owner_id="someone-else")
    db = _db(map_obj)

    with patch("main.clean_user_stream", AsyncMock()) as clean:
        with pytest.raises(HTTPException) as exc:
            await unlink_map(map_id="map-1", user=_user("user-1"), db=db)

    assert exc.value.status_code == 401
    assert map_obj.is_live is True
    assert map_obj.bot_active is True
    db.commit.assert_not_called()
    clean.assert_not_awaited()
