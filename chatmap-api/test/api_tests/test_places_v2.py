from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from api.v2.schemas.places import MAX_PLACE_NAMES, PlaceNames
from db import Point
from results.error import UnknownPoint
from store.place_names_store import PlaceNamesStore


def test_the_other_names_of_a_place_are_each_once_however_cased_and_spaced():
    assert PlaceNames(names=[" Ein  Rihan ", "ein rihan", "", "عين الريحان"]).names == ["Ein Rihan", "عين الريحان"]


@pytest.mark.parametrize("names", [[f"name {i}" for i in range(MAX_PLACE_NAMES + 1)], ["x" * 101]])
def test_a_place_has_a_limited_number_of_other_names_of_a_limited_length(names):
    with pytest.raises(ValidationError):
        PlaceNames(names=names)


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch("store.place_names_store.session_scope", scope)


# Another owner, a removed place, a report
@pytest.mark.parametrize("owner, removed, place", [("user-2", False, True), ("user-1", True, True), ("user-1", False, False)])
async def test_only_the_owner_writes_the_names_of_a_place_not_removed(owner, removed, place):
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = SimpleNamespace(
        Point=Point(id="p-1", removed=removed, place=place), owner_id=owner,
    )

    with _patch_scope(db), pytest.raises(UnknownPoint):
        await PlaceNamesStore.set_names("p-1", "user-1", ["a"])
    db.commit.assert_not_called()


async def test_the_names_of_a_place_are_replaced_in_their_order():
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = SimpleNamespace(Point=Point(id="p-1", map_id="map-1", removed=False, place=True), owner_id="user-1")

    with _patch_scope(db):
        assert await PlaceNamesStore.set_names("p-1", "user-1", ["el puente", "الجسر"]) == ("map-1", ["el puente", "الجسر"])

    added = list(db.add_all.call_args.args[0])
    assert [(row.name, row.position) for row in added] == [("el puente", 0), ("الجسر", 1)]
    db.commit.assert_called_once()
