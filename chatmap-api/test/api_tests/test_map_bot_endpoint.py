import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

# main.py wires up hotosm_auth_fastapi at import time, which requires these to
# be set even though these tests never talk to Hanko. Set only if missing, so
# real values (e.g. running inside the app container) still take precedence.
os.environ.setdefault("HANKO_API_URL", "http://localhost:8002")
os.environ.setdefault("COOKIE_SECRET", "dev-secret-key-min-32-bytes-long!")

from bot.configured_messages import BotStep
from db import Map
from main import get_bot_setup, set_bot_setup
from schemas import BotConfiguredMessage, BotMaxAttemptsMessages, BotSetup


def _map(owner_id="user-1", bot_active=False):
    return Map(id="map-1", owner_id=owner_id, bot_active=bot_active)


def _db(map_obj):
    db = MagicMock(spec=Session)
    db.get.return_value = map_obj
    return db


def _user(user_id="user-1"):
    return SimpleNamespace(id=user_id)


def _stored_message(bot_step, item_id="item-1", position=None, prompt="a message", error_message=None, options=None):
    return SimpleNamespace(
        id=item_id, bot_step=bot_step, position=position,
        content=prompt, error_message=error_message, options=options or [],
    )


def _stored_attempts(item_id="attempts-1", max_attempts_quantity=3,
                     notify_message="Too many tries", to_restart="Restart", to_cancel="Cancel"):
    return SimpleNamespace(
        id=item_id, bot_step=BotStep.MAX_ATTEMPTS, max_attempts_quantity=max_attempts_quantity,
        content=notify_message, to_restart=to_restart, to_cancel=to_cancel,
    )


def _complete_messages():
    """The smallest message list that lets the bot be enabled."""
    return [
        BotConfiguredMessage(bot_step=BotStep.START, prompt="Hi, I'm the ChatMap bot"),
        BotConfiguredMessage(bot_step=BotStep.MEDIA, prompt="Send the content", error_message="That is not a photo"),
        BotConfiguredMessage(bot_step=BotStep.LOCATION, prompt="Now share the location",
                             error_message="That is not a location"),
        BotConfiguredMessage(bot_step=BotStep.END, prompt="Done, it is on the map"),
    ]


def _complete_max_attempts():
    return BotMaxAttemptsMessages(
        max_attempts_quantity=3, notify_message="Too many tries", to_restart="Restart", to_cancel="Cancel",
    )


def _question(prompt="Main material?", error_message="Pick one of the options", options=None):
    return BotConfiguredMessage(
        bot_step=BotStep.SINGLE_CHOICE, position=0, prompt=prompt,
        error_message=error_message, options=options if options is not None else ["Bricks", "Wood"],
    )


# ---- read ----

async def test_owner_reads_bot_setup():
    db = _db(_map(bot_active=True))
    stored = [_stored_message(BotStep.START, prompt="Hi")]

    with patch("main.get_configured_messages", return_value=stored) as fetch:
        result = await get_bot_setup(map_id="map-1", user=_user(), db=db)

    assert result.bot_active is True
    assert [(message.bot_step, message.prompt) for message in result.messages] == [(BotStep.START, "Hi")]
    fetch.assert_called_once_with("map-1")


async def test_an_unconfigured_map_reads_back_empty():
    db = _db(_map(bot_active=False))

    with patch("main.get_configured_messages", return_value=[]):
        result = await get_bot_setup(map_id="map-1", user=_user(), db=db)

    assert result.bot_active is False
    assert result.messages == []


async def test_non_owner_cannot_read_bot_setup():
    db = _db(_map(owner_id="another-user", bot_active=True))

    with pytest.raises(HTTPException) as exc_info:
        await get_bot_setup(map_id="map-1", user=_user("user-1"), db=db)

    assert exc_info.value.status_code == 401


async def test_reading_a_missing_map_is_unauthorized():
    db = _db(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_bot_setup(map_id="does-not-exist", user=_user(), db=db)

    assert exc_info.value.status_code == 401


async def test_anonymous_user_cannot_read_bot_setup():
    db = _db(_map(bot_active=True))

    with pytest.raises(HTTPException) as exc_info:
        await get_bot_setup(map_id="map-1", user=None, db=db)

    assert exc_info.value.status_code == 401


# ---- write ----

async def test_owner_saves_messages_and_enables_the_bot():
    map_obj = _map(bot_active=False)
    db = _db(map_obj)
    messages = _complete_messages()
    stored = [_stored_message(BotStep.START, prompt="Hi, I'm the ChatMap bot"), _stored_attempts()]

    with patch("main.update_configured_messages", return_value=stored) as replace:
        result = await set_bot_setup(
            map_id="map-1",
            bot_data=BotSetup(bot_active=True, messages=messages, max_attempts_messages=_complete_max_attempts()),
            user=_user(),
            db=db,
        )

    assert result.bot_active is True
    assert map_obj.bot_active is True
    saved = replace.call_args.kwargs["messages"]
    assert [item["bot_step"] for item in saved] == [message.bot_step for message in messages] + [BotStep.MAX_ATTEMPTS]
    db.commit.assert_called_once()


async def test_saving_passes_item_ids_through_so_edits_keep_them():
    db = _db(_map())
    messages = _complete_messages() + [_question()]
    messages[0].id = "existing-start"

    with patch("main.update_configured_messages", return_value=[]) as replace:
        await set_bot_setup(
            map_id="map-1",
            bot_data=BotSetup(bot_active=False, messages=messages, max_attempts_messages=BotMaxAttemptsMessages()),
            user=_user(),
            db=db,
        )

    saved = replace.call_args.kwargs["messages"]
    assert saved[0]["id"] == "existing-start"
    question_row = next(item for item in saved if item["bot_step"] == BotStep.SINGLE_CHOICE)
    assert question_row["id"] is None


async def test_owner_disables_the_bot():
    map_obj = _map(bot_active=True)
    db = _db(map_obj)

    with patch("main.update_configured_messages", return_value=[]):
        result = await set_bot_setup(
            map_id="map-1",
            bot_data=BotSetup(bot_active=False, messages=[], max_attempts_messages=BotMaxAttemptsMessages()),
            user=_user(),
            db=db,
        )

    assert result.bot_active is False
    assert map_obj.bot_active is False


# ---- unauthorized ----

async def test_non_owner_cannot_change_bot_setup():
    map_obj = _map(owner_id="another-user", bot_active=False)
    db = _db(map_obj)

    with patch("main.update_configured_messages") as replace:
        with pytest.raises(HTTPException) as exc_info:
            await set_bot_setup(
                map_id="map-1",
                bot_data=BotSetup(bot_active=True, messages=_complete_messages(),
                                  max_attempts_messages=_complete_max_attempts()),
                user=_user("user-1"),
                db=db,
            )

    assert exc_info.value.status_code == 401
    assert map_obj.bot_active is False
    replace.assert_not_called()
    db.commit.assert_not_called()


async def test_saving_a_missing_map_is_unauthorized():
    db = _db(None)

    with patch("main.update_configured_messages") as replace:
        with pytest.raises(HTTPException) as exc_info:
            await set_bot_setup(
                map_id="does-not-exist",
                bot_data=BotSetup(bot_active=False, messages=[], max_attempts_messages=BotMaxAttemptsMessages()),
                user=_user(),
                db=db,
            )

    assert exc_info.value.status_code == 401
    replace.assert_not_called()


async def test_anonymous_user_cannot_change_bot_setup():
    map_obj = _map(bot_active=False)
    db = _db(map_obj)

    with patch("main.update_configured_messages") as replace:
        with pytest.raises(HTTPException) as exc_info:
            await set_bot_setup(
                map_id="map-1",
                bot_data=BotSetup(bot_active=False, messages=[], max_attempts_messages=BotMaxAttemptsMessages()),
                user=None,
                db=db,
            )

    assert exc_info.value.status_code == 401
    assert map_obj.bot_active is False
    replace.assert_not_called()


# ---- validation ----

def test_a_complete_configuration_can_enable_the_bot():
    setup = BotSetup(bot_active=True, messages=_complete_messages(), max_attempts_messages=_complete_max_attempts())

    assert setup.bot_active is True


def test_the_bot_cannot_be_enabled_with_no_messages():
    with pytest.raises(ValidationError, match="cannot be enabled without a 'start' message"):
        BotSetup(bot_active=True, messages=[], max_attempts_messages=BotMaxAttemptsMessages())


@pytest.mark.parametrize("missing", ["start", "media", "location", "end"])
def test_the_bot_cannot_be_enabled_with_a_required_message_missing(missing):
    messages = [message for message in _complete_messages() if message.bot_step.value != missing]

    with pytest.raises(ValidationError, match=f"without a '{missing}' message"):
        BotSetup(bot_active=True, messages=messages, max_attempts_messages=_complete_max_attempts())


@pytest.mark.parametrize("kind", ["media", "location"])
def test_the_bot_cannot_be_enabled_without_an_incorrect_answer_for_an_answering_step(kind):
    messages = _complete_messages()
    for message in messages:
        if message.bot_step.value == kind:
            message.error_message = "  "

    with pytest.raises(ValidationError, match=f"incorrect answer for '{kind}'"):
        BotSetup(bot_active=True, messages=messages, max_attempts_messages=_complete_max_attempts())


def test_the_bot_cannot_be_enabled_without_the_max_attempts_message():
    max_attempts_messages = BotMaxAttemptsMessages(
        max_attempts_quantity=3, notify_message="", to_restart="Restart", to_cancel="Cancel",
    )

    with pytest.raises(ValidationError, match="max attempts message and its two options"):
        BotSetup(bot_active=True, messages=_complete_messages(), max_attempts_messages=max_attempts_messages)


def test_the_max_attempts_quantity_must_be_at_least_one():
    max_attempts_messages = BotMaxAttemptsMessages(
        max_attempts_quantity=0, notify_message="Too many tries", to_restart="Restart", to_cancel="Cancel",
    )

    with pytest.raises(ValidationError, match="max attempts quantity must be at least 1"):
        BotSetup(bot_active=True, messages=_complete_messages(), max_attempts_messages=max_attempts_messages)


def test_max_attempts_cannot_be_configured_as_a_regular_message():
    messages = [BotConfiguredMessage(bot_step=BotStep.MAX_ATTEMPTS, prompt="Too many tries")]

    with pytest.raises(ValidationError, match="configured through 'max_attempts_messages'"):
        BotSetup(bot_active=False, messages=messages, max_attempts_messages=BotMaxAttemptsMessages())


def test_an_incomplete_configuration_can_still_be_saved_while_the_bot_is_off():
    setup = BotSetup(
        bot_active=False, messages=[BotConfiguredMessage(bot_step=BotStep.START, prompt="Hi")],
        max_attempts_messages=BotMaxAttemptsMessages(),
    )

    assert setup.bot_active is False
    assert len(setup.messages) == 1


def test_the_bot_can_be_enabled_with_no_questions():
    setup = BotSetup(bot_active=True, messages=_complete_messages(), max_attempts_messages=_complete_max_attempts())

    assert [message for message in setup.messages if message.bot_step == BotStep.SINGLE_CHOICE] == []


def test_a_question_without_text_is_rejected_even_with_the_bot_off():
    with pytest.raises(ValidationError, match="needs its question text"):
        BotSetup(
            bot_active=False, messages=[_question(prompt="   ")], max_attempts_messages=BotMaxAttemptsMessages(),
        )


def test_a_question_without_an_incorrect_answer_is_rejected():
    with pytest.raises(ValidationError, match="needs an incorrect answer message"):
        BotSetup(
            bot_active=False, messages=[_question(error_message="")], max_attempts_messages=BotMaxAttemptsMessages(),
        )


@pytest.mark.parametrize("options", [[], ["Only one"], [f"Option {i}" for i in range(11)]])
def test_a_question_needs_between_two_and_ten_options(options):
    with pytest.raises(ValidationError, match="between 2 and 10 options"):
        BotSetup(
            bot_active=False, messages=[_question(options=options)], max_attempts_messages=BotMaxAttemptsMessages(),
        )


def test_a_fixed_kind_cannot_be_configured_twice():
    messages = _complete_messages() + [BotConfiguredMessage(bot_step=BotStep.START, prompt="Hi again")]

    with pytest.raises(ValidationError, match="'start' can only be configured once"):
        BotSetup(bot_active=False, messages=messages, max_attempts_messages=BotMaxAttemptsMessages())


def test_several_questions_are_allowed():
    messages = _complete_messages() + [_question(prompt="First"), _question(prompt="Second")]

    setup = BotSetup(bot_active=True, messages=messages, max_attempts_messages=_complete_max_attempts())

    assert len([message for message in setup.messages if message.bot_step == BotStep.SINGLE_CHOICE]) == 2


# ---- free text questions ----

def _free_text_question(prompt="Describe the damage", error_message="Please send a text message", options=None):
    return BotConfiguredMessage(
        bot_step=BotStep.FREE_TEXT, position=0, prompt=prompt,
        error_message=error_message, options=options or [],
    )


def test_a_free_text_question_is_accepted_with_a_prompt_and_an_error_message():
    setup = BotSetup(
        bot_active=False, messages=[_free_text_question()], max_attempts_messages=BotMaxAttemptsMessages(),
    )

    assert [m.bot_step for m in setup.messages if m.bot_step == BotStep.FREE_TEXT] == [BotStep.FREE_TEXT]


def test_a_free_text_question_without_text_is_rejected():
    with pytest.raises(ValidationError, match="needs its question text"):
        BotSetup(
            bot_active=False, messages=[_free_text_question(prompt="  ")],
            max_attempts_messages=BotMaxAttemptsMessages(),
        )


def test_a_free_text_question_without_an_incorrect_answer_is_rejected():
    with pytest.raises(ValidationError, match="needs an incorrect answer message"):
        BotSetup(
            bot_active=False, messages=[_free_text_question(error_message="")],
            max_attempts_messages=BotMaxAttemptsMessages(),
        )


def test_a_free_text_question_cannot_carry_options():
    with pytest.raises(ValidationError, match="free text question takes no options"):
        BotSetup(
            bot_active=False, messages=[_free_text_question(options=["Yes", "No"])],
            max_attempts_messages=BotMaxAttemptsMessages(),
        )


def test_free_text_and_single_choice_questions_can_be_mixed_and_enable_the_bot():
    messages = _complete_messages() + [_question(prompt="Material?"), _free_text_question(prompt="Anything else?")]

    setup = BotSetup(bot_active=True, messages=messages, max_attempts_messages=_complete_max_attempts())

    assert [m.bot_step for m in setup.messages if m.bot_step in (BotStep.SINGLE_CHOICE, BotStep.FREE_TEXT)] == [
        BotStep.SINGLE_CHOICE, BotStep.FREE_TEXT
    ]
