from unittest.mock import MagicMock, patch

import pytest

from data import has_valid_location, process_chat_entries


@pytest.mark.parametrize("location, valid", [
    ("", True), ("-34.6,-58.4", True), ("-34.6037, -58.3816", True),
    ("test location 0", False), ("-34.6", False), ("a,b", False), ("1,2,3", False),
])
def test_a_location_is_two_numbers_or_none(location, valid):
    assert has_valid_location({"location": location}) == valid
    assert has_valid_location({})


def _entries(*locations):
    return [(f"{i}-0", {b"location": location.encode(), b"message": b""}) for i, location in enumerate(locations)]


async def test_an_entry_with_a_location_that_is_not_two_numbers_does_not_stop_the_others():
    with patch("data.get_db_session", return_value=MagicMock()), \
            patch("data.chatmap_parser.streamParser", return_value={"features": []}) as parse, \
            patch("data.add_points") as add:
        await process_chat_entries("user-1", _entries("test location 0", "-34.6,-58.4"))

    assert [entry["location"] for entry in parse.call_args.args[0]] == ["-34.6,-58.4"]
    add.assert_not_called()


async def test_a_chat_the_parser_cannot_read_adds_no_points_and_does_not_fail():
    with patch("data.get_db_session", return_value=MagicMock()), \
            patch("data.chatmap_parser.streamParser", side_effect=IndexError("list index out of range")), \
            patch("data.add_points") as add:
        await process_chat_entries("user-1", _entries("-34.6,-58.4"))

    add.assert_not_called()
