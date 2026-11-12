from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from db import GroupMessage, MapKey, MessageSuggestion, PointTag, PointTagChange
from results.error import MessageDismissed, UnknownMessage, UnknownSuggestion
from store.message_suggestions_store import MessageSuggestionsStore

SENT_AT = datetime(2026, 10, 22, 12, tzinfo=UTC)
STATUS = MapKey(id="k-1", map_id="map-1", key="Status", single=True, closed=True)
STORE = "store.message_suggestions_store"


def _patch_scope(db):
    scope = MagicMock()
    scope.return_value.__enter__.return_value = db
    scope.return_value.__exit__.return_value = False
    return patch(f"{STORE}.session_scope", scope)


def _suggestion(suggestion_id="s-1", value_id="v-1", state="pending", point_id="p-1", line=0):
    return MessageSuggestion(
        id=suggestion_id, message_id="m-1", line=line, point_id=point_id, key_id="k-1", value_id=value_id,
        words=["Puente", "cerrado"], doubt=None, state=state,
    )


def _rows(*rows):
    result = MagicMock()
    result.all.return_value = list(rows)
    return result


def _scalars(*items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(items)
    result.scalars.return_value.__iter__ = lambda self: iter(list(items))
    return result


def _message(dismissed_at=None):
    return GroupMessage(id="m-1", map_id="map-1", group_id="group-1", sent_at=SENT_AT, dismissed_at=dismissed_at)


async def test_the_suggestions_of_messages_say_whether_their_places_have_that_value_now():
    db = MagicMock()
    db.execute.side_effect = [
        _scalars(_suggestion(), _suggestion("s-2", "v-2", point_id="p-2")),
        _rows(("p-1", "k-1", "v-1"), ("p-2", "k-1", "v-1")),
    ]

    with _patch_scope(db):
        found = await MessageSuggestionsStore.suggestions("user-1", ["m-1"])

    assert [(row.id, unchanged) for row, unchanged in found["m-1"]] == [("s-1", True), ("s-2", False)]
    # Only the ones of maps the user owns
    assert "maps.owner_id" in str(db.execute.call_args_list[0].args[0])


async def test_no_to_a_suggestion_rejects_it_taking_it_back_makes_it_pending_and_a_confirmed_one_stays():
    suggestion = _suggestion()
    db = MagicMock()
    db.get.return_value = suggestion

    with _patch_scope(db), patch(f"{STORE}._owned_message"):
        assert await MessageSuggestionsStore.set_rejected("s-1", "user-1", True) == "m-1"
        assert suggestion.state == "rejected"
        await MessageSuggestionsStore.set_rejected("s-1", "user-1", False)
        assert (suggestion.state, suggestion.answered_at) == ("pending", None)
        suggestion.state = "accepted"
        await MessageSuggestionsStore.set_rejected("s-1", "user-1", True)
        assert suggestion.state == "accepted"


@pytest.mark.parametrize("owned", [True, False])
async def test_a_suggestion_that_does_not_exist_or_is_of_a_map_of_another_is_not_found(owned):
    db = MagicMock()
    db.get.return_value = _suggestion() if not owned else None

    with _patch_scope(db), patch(f"{STORE}._owned_message", side_effect=UnknownMessage("m-1")), \
            pytest.raises(UnknownSuggestion):
        await MessageSuggestionsStore.set_rejected("s-1", "user-1", True)


async def test_renewing_confirms_at_the_time_of_the_message_only_what_places_of_its_map_still_have():
    same, changed = _suggestion(), _suggestion("s-2", point_id="p-2")
    # p-3 is not a place of the map of the message (another map, or removed): the lock does not give it
    elsewhere = _suggestion("s-3", point_id="p-3", line=1)
    by_words = MessageSuggestion(**{**_dict(same), "id": "s-4", "line": 2})
    db = MagicMock()
    db.execute.side_effect = [
        _scalars(same, changed, elsewhere, by_words), _scalars("p-1", "p-2"), _scalars(STATUS),
        # p-1 still has v-1; p-2 has another value by now
        _rows(("p-1", "k-1", "v-1"), ("p-2", "k-1", "v-9")),
    ]
    same.rule_id = "r-1"
    change = PointTagChange(id=7, point_id="p-1", key_id="k-1", value_id="v-1", happened_at=SENT_AT)
    tag = PointTag(point_id="p-1", key_id="k-1", value_id="v-1", since=SENT_AT, confirmed_at=SENT_AT)

    with _patch_scope(db), \
            patch(f"{STORE}._owned_message", return_value=_message()), \
            patch(f"{STORE}.give_tag", return_value=(change, [tag])) as give:
        assert [made.id for made in await MessageSuggestionsStore.renew("m-1", "user-1", ["s-1", "s-2", "s-3", "s-4"])] == [7, 7]

    assert [call.args[1:7] for call in give.call_args_list] == [("p-1", STATUS, "set", "v-1", None, SENT_AT)] * 2
    # What a rule suggested is the rule's; what the words suggested, the message's
    assert [call.kwargs["source"] for call in give.call_args_list] == ["rule", "message"]
    assert (same.state, changed.state, elsewhere.state, by_words.state) == ("accepted", "pending", "pending", "accepted")
    db.commit.assert_called_once()


async def test_a_dismissed_message_renews_nothing():
    db = MagicMock()
    with _patch_scope(db), patch(f"{STORE}._owned_message", return_value=_message(dismissed_at=SENT_AT)), \
            pytest.raises(MessageDismissed):
        await MessageSuggestionsStore.renew("m-1", "user-1", ["s-1"])


async def test_reading_again_makes_the_pending_suggestions_again_but_not_what_a_person_answered():
    db = MagicMock()
    db.execute.side_effect = [
        _scalars("m-1", "m-2"),
        _rows(
            SimpleNamespace(id="m-1", group_id="group-1", text="Puente cerrado", dismissed_at=None, chat="c-1"),
            # Hidden by a rule that no longer hides it
            SimpleNamespace(id="m-2", group_id="group-1", text="Hola a todos", dismissed_at=SENT_AT, chat="c-1"),
        ),
        _scalars(_suggestion(state="rejected")), MagicMock(), MagicMock(), MagicMock(),
    ]
    again = {"m-1": [
        # What the person said no to is not suggested again; what is new is
        {**_dict(_suggestion()), "id": "n-1"}, {**_dict(_suggestion(value_id="v-2")), "id": "n-2"},
    ]}

    with _patch_scope(db), patch(f"{STORE}.suggest", return_value=again) as suggest:
        assert await MessageSuggestionsStore.reread("map-1") == 1

    assert suggest.call_args.args[3] == {"m-1": "c-1", "m-2": "c-1"}
    assert [(row["id"], row["dismissed_at"]) for row in db.execute.call_args_list[4].args[1]] == [("m-1", None), ("m-2", None)]
    inserted = db.execute.call_args_list[5].args[0].compile().params
    assert [value for name, value in inserted.items() if name.startswith("id_")] == ["n-2"]
    db.commit.assert_called_once()


def _dict(suggestion: MessageSuggestion) -> dict:
    return {column: getattr(suggestion, column) for column in (
        "message_id", "line", "point_id", "key_id", "value_id", "words", "doubt", "state",
    )} | {"rule_id": None, "rule": None}
