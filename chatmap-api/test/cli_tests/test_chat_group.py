from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy.exc import NoResultFound
from typer.testing import CliRunner

from cli.cli import app
from results.error import UnknownGroup
from store.group_messages_store import pseudonym

runner = CliRunner()


def _invoke(*args, **store):
    mocks = {name: AsyncMock(**kwargs) for name, kwargs in store.items()}
    with patch("cli.cli.get_live_map_id", return_value="map-1"), patch("cli.cli.session_scope"), \
            patch.multiple("cli.cli.GroupMessagesStore", **mocks):
        result = runner.invoke(app, ["chat-group", *args])
    return result, SimpleNamespace(**mocks)


def test_enable_makes_the_live_map_listen_to_the_group_as_if_picked_from_the_phone():
    group = SimpleNamespace(name="Test group", chat="c-1")

    result, store = _invoke(
        "enable", "--device", "demo", "--chat", "group-north", "--name", "Test group",
        set_group={"return_value": group},
    )

    assert result.exit_code == 0
    store.set_group.assert_awaited_once_with(
        "map-1", "demo", pseudonym("map-1", "group-north"), True, False,
        [{"chat": "group-north", "name": "Test group"}],
    )


def test_disable_can_also_remove_the_messages_of_the_group():
    result, store = _invoke(
        "disable", "--device", "demo", "--chat", "group-north", "--delete-messages",
        set_group={"return_value": SimpleNamespace(name="Test group", chat="c-1")},
    )

    assert result.exit_code == 0
    store.set_group.assert_awaited_once_with("map-1", "demo", pseudonym("map-1", "group-north"), False, True, [])


def test_disable_a_group_the_map_does_not_have():
    result, _ = _invoke("disable", "--device", "demo", "--chat", "nope", set_group={"side_effect": UnknownGroup("x")})

    assert result.exit_code == 1
    assert "does not have the group" in result.output


def test_a_device_without_live_map():
    with patch("cli.cli.get_live_map_id", side_effect=NoResultFound()), patch("cli.cli.session_scope"):
        result = runner.invoke(app, ["chat-group", "list", "--device", "demo"])

    assert result.exit_code == 1
    assert "has no live map" in result.output


def test_list_shows_the_groups_the_map_keeps():
    groups = [SimpleNamespace(chat="c-1", name="Test group", enabled=True)]

    result, _ = _invoke("list", "--device", "demo", groups={"return_value": (groups, 30)})

    assert result.exit_code == 0
    assert "30 days" in result.output
    assert "Test group" in result.output
