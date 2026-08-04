from datetime import datetime, timezone
from unittest.mock import AsyncMock, call, patch

import pytest

from bot.flow import BotFlowContext, Language
from bot.flows.first_time_mapping import flow as flow_module
from bot.flows.first_time_mapping.flow import (
    FirstTimeMappingFlow,
    FirstTimeMappingState,
    translations,
    _build_options_message,
    _lang_options,
)
from conversation_engine.event import EventName
from results.error import BotStateWithoutPointId
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore
from store.survey_responses_store import SurveyResponsesStore


OCCURRED_AT = datetime(2026, 8, 9, 21, 7, 41, tzinfo=timezone.utc)


def _make_flow(state, language=Language.ES, bot_state_store=None, message_to_send_store=None,
               bot_consumed_messages_store=None, survey_responses_store=None):
    return FirstTimeMappingFlow(
        state=state,
        language=language,
        bot_state_store=bot_state_store or AsyncMock(spec=BotStateStore),
        message_to_send_store=message_to_send_store or AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=bot_consumed_messages_store or AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=survey_responses_store or AsyncMock(spec=SurveyResponsesStore),
    )


def _ctx(**overrides):
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_field.return_value = None

    fields = dict(
        state_key="key-1", recipient="user-enc-1", sender="device-1", answer="", message_id="msg-1",
        occurred_at=OCCURRED_AT, point_id=None, bot_state_store=bot_state_store,
    )
    fields.update(overrides)
    return BotFlowContext(**fields)


# ---- create() ----

async def test_create_defaults_to_idle_and_default_language_when_no_state_stored():
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_state.return_value = {}

    flow = await FirstTimeMappingFlow.create(
        bot_state_key="key-1",
        bot_state_store=bot_state_store,
        message_to_send_store=AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=AsyncMock(spec=SurveyResponsesStore),
    )

    assert flow.state == FirstTimeMappingState.IDLE
    assert flow.language == Language.default()
    bot_state_store.fetch_state.assert_awaited_once_with(bot_state_key="key-1")


@pytest.mark.parametrize("stored_state, stored_lang, expected_state, expected_lang", [
    ("WAITING_LANG", "ES", FirstTimeMappingState.WAITING_LANG, Language.ES),
    ("WAITING_PHOTO", "EN", FirstTimeMappingState.WAITING_PHOTO, Language.EN),
    ("WAITING_COORDINATES", "PT", FirstTimeMappingState.WAITING_COORDINATES, Language.PT),
    ("WAITING_DAMAGE_LEVEL", "PT", FirstTimeMappingState.WAITING_DAMAGE_LEVEL, Language.PT),
    ("MAPPING_COMPLETED", "FR", FirstTimeMappingState.MAPPING_COMPLETED, Language.FR),
])
async def test_create_restores_previously_stored_state_and_language(
        stored_state, stored_lang, expected_state, expected_lang):
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_state.return_value = {"state": stored_state, "lang": stored_lang}

    flow = await FirstTimeMappingFlow.create(
        bot_state_key="key-1",
        bot_state_store=bot_state_store,
        message_to_send_store=AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=AsyncMock(spec=SurveyResponsesStore),
    )

    assert flow.state == expected_state
    assert flow.language == expected_lang


async def test_create_falls_back_to_idle_for_an_unrecognized_state():
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_state.return_value = {"state": "NOT_A_REAL_STATE", "lang": "EN"}

    flow = await FirstTimeMappingFlow.create(
        bot_state_key="key-1",
        bot_state_store=bot_state_store,
        message_to_send_store=AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=AsyncMock(spec=SurveyResponsesStore),
    )

    assert flow.state == FirstTimeMappingState.IDLE
    assert flow.language == Language.EN


async def test_create_falls_back_to_default_language_for_an_unrecognized_language():
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_state.return_value = {"state": "WAITING_PHOTO", "lang": "DE"}

    flow = await FirstTimeMappingFlow.create(
        bot_state_key="key-1",
        bot_state_store=bot_state_store,
        message_to_send_store=AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=AsyncMock(spec=SurveyResponsesStore),
    )

    assert flow.state == FirstTimeMappingState.WAITING_PHOTO
    assert flow.language == Language.default()


# ---- transitions table wiring ----

@pytest.mark.parametrize("state, event, handler_name", [
    (FirstTimeMappingState.IDLE, EventName.USER_SEND_TEXT, "on_ask_for_help"),
    (FirstTimeMappingState.WAITING_LANG, EventName.USER_SEND_TEXT, "on_ask_for_lang"),
    (FirstTimeMappingState.WAITING_PHOTO, EventName.USER_UPLOAD_PHOTO, "on_photo_uploaded"),
    (FirstTimeMappingState.WAITING_COORDINATES, EventName.USER_SEND_COORDINATES, "on_coordinates_sent"),
    (FirstTimeMappingState.WAITING_DAMAGE_LEVEL, EventName.USER_SEND_TEXT, "on_damage_level_answered"),
    (FirstTimeMappingState.WAITING_RECOVERY_CHOICE, EventName.USER_SEND_TEXT, "on_recovery_choice_answered"),
])
def test_transitions_table_wiring(state, event, handler_name):
    assert FirstTimeMappingFlow.transitions[(state, event)] is getattr(FirstTimeMappingFlow, handler_name)


def test_transitions_table_has_no_unexpected_entries():
    assert len(FirstTimeMappingFlow.transitions) == 6


# ---- call() dispatch ----

async def test_call_awaits_the_matching_handler_with_self_and_context():
    mock_handler = AsyncMock()
    flow = _make_flow(FirstTimeMappingState.IDLE)
    flow.transitions = {
        (FirstTimeMappingState.IDLE, EventName.USER_SEND_TEXT): mock_handler
    }
    ctx = _ctx()

    await flow.call(EventName.USER_SEND_TEXT, ctx)

    mock_handler.assert_awaited_once_with(flow, ctx)


async def test_call_does_not_invoke_a_handler_for_a_different_state_or_event():
    mock_handler = AsyncMock()
    flow = _make_flow(FirstTimeMappingState.WAITING_PHOTO)
    flow.transitions = {
        (FirstTimeMappingState.IDLE, EventName.USER_SEND_TEXT): mock_handler
    }
    ctx = _ctx()

    await flow.call(EventName.USER_SEND_TEXT, ctx)

    mock_handler.assert_not_awaited()


async def test_call_reports_a_missing_handler():
    flow = _make_flow(FirstTimeMappingState.MAPPING_COMPLETED)
    ctx = _ctx()

    with patch.object(flow_module, "not_handler_created") as mock_not_handler_created:
        await flow.call(EventName.USER_SEND_TEXT, ctx)

    mock_not_handler_created.assert_called_once_with(
        flow.name, FirstTimeMappingState.MAPPING_COMPLETED, EventName.USER_SEND_TEXT
    )


async def test_call_invokes_on_fallback_when_no_handler_matches():
    message_store = AsyncMock(spec=MessageToSendStore)
    flow = _make_flow(FirstTimeMappingState.MAPPING_COMPLETED, message_to_send_store=message_store)
    ctx = _ctx()

    with patch.object(flow_module, "not_handler_created"):
        await flow.call(EventName.USER_SEND_TEXT, ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=translations[flow.language.name]["fallback"],
    )


# ---- handler behavior ----

@pytest.mark.parametrize("language", list(Language))
async def test_on_ask_for_help_sends_tutorial_in_current_language_and_moves_to_waiting_lang(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.IDLE, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_ask_for_help(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(translations[language.name]["ask_for_lang_question"], _lang_options()),
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_LANG,
        bot_info={"fallback_count": "0"},
    )


@pytest.mark.parametrize("answer, expected_language", [
    ("1", Language.ES),
    ("2", Language.EN),
    ("3", Language.PT),
    ("4", Language.FR),
])
async def test_on_ask_for_lang_resolves_the_selected_language(answer, expected_language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_LANG, Language.ES, bot_state_store, message_store)
    ctx = _ctx(answer=answer)

    await flow.on_ask_for_lang(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=translations[expected_language.name]["ask_for_photo"],
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_PHOTO,
        bot_info={"lang": expected_language.name, "fallback_count": "0"},
    )


async def test_on_ask_for_lang_reasks_in_current_language_for_an_invalid_option():
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_LANG, Language.EN, bot_state_store, message_store)
    ctx = _ctx(answer="9")

    await flow.on_ask_for_lang(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(translations["EN"]["ask_for_lang_question"], _lang_options()),
    )
    bot_state_store.save_state.assert_not_awaited()


@pytest.mark.parametrize("language", list(Language))
async def test_on_photo_uploaded_asks_for_coordinates_in_current_language(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_PHOTO, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_photo_uploaded(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=translations[language.name]["ask_for_coordinate"],
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_COORDINATES,
        bot_info={"fallback_count": "0"},
    )


@pytest.mark.parametrize("language", list(Language))
async def test_on_coordinates_sent_asks_for_damage_level_and_stores_point_id(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_COORDINATES, language, bot_state_store, message_store)
    ctx = _ctx(point_id="point-99")

    await flow.on_coordinates_sent(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(
            translations[language.name]["damage_level_question"], translations[language.name]["damage_level_options"]
        ),
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_DAMAGE_LEVEL,
        bot_info={"point_id": "point-99", "fallback_count": "0"},
    )


@pytest.mark.parametrize("language, answer, expected_label", [
    (Language.ES, "1", "Alto"),
    (Language.ES, "2", "Medio"),
    (Language.ES, "3", "Bajo"),
    (Language.EN, "1", "High"),
    (Language.PT, "2", "Médio"),
    (Language.FR, "3", "Faible"),
])
async def test_on_damage_level_answered_persists_response_and_completes_the_flow(language, answer, expected_label):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    survey_responses_store = AsyncMock(spec=SurveyResponsesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_DAMAGE_LEVEL, language, bot_state_store, message_store,
        survey_responses_store=survey_responses_store,
    )
    ctx_bot_state_store = AsyncMock(spec=BotStateStore)
    ctx_bot_state_store.fetch_field.return_value = "point-99"
    ctx = _ctx(answer=answer, bot_state_store=ctx_bot_state_store)

    await flow.on_damage_level_answered(ctx)

    ctx_bot_state_store.fetch_field.assert_awaited_once_with(bot_state_key=ctx.state_key, field="point_id")
    survey_responses_store.add_response.assert_awaited_once_with(
        point_id="point-99",
        question=translations[language.name]["damage_level_question"],
        answer=expected_label,
    )
    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=translations[language.name]["end_flow"],
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.MAPPING_COMPLETED,
        bot_info={"fallback_count": "0"},
    )
    bot_state_store.delete_state.assert_awaited_once_with(bot_state_key=ctx.state_key)
    assert [call[0] for call in bot_state_store.method_calls] == ["save_state", "delete_state"]


async def test_on_damage_level_answered_raises_when_point_id_is_missing_from_state():
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    survey_responses_store = AsyncMock(spec=SurveyResponsesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_DAMAGE_LEVEL, Language.EN, bot_state_store, message_store,
        survey_responses_store=survey_responses_store,
    )
    ctx_bot_state_store = AsyncMock(spec=BotStateStore)
    ctx_bot_state_store.fetch_field.return_value = None
    ctx = _ctx(answer="1", message_id="reply-msg-1", bot_state_store=ctx_bot_state_store)

    with pytest.raises(BotStateWithoutPointId) as exc_info:
        await flow.on_damage_level_answered(ctx)

    assert exc_info.value.message_id == "reply-msg-1"
    survey_responses_store.add_response.assert_not_awaited()
    bot_state_store.save_state.assert_not_awaited()
    bot_state_store.delete_state.assert_not_awaited()


async def test_on_damage_level_answered_reasks_for_an_invalid_option_without_persisting():
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    survey_responses_store = AsyncMock(spec=SurveyResponsesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_DAMAGE_LEVEL, Language.EN, bot_state_store, message_store,
        survey_responses_store=survey_responses_store,
    )
    ctx = _ctx(answer="9")

    await flow.on_damage_level_answered(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(
            translations["EN"]["damage_level_question"], translations["EN"]["damage_level_options"]
        ),
    )
    survey_responses_store.add_response.assert_not_awaited()
    bot_state_store.save_state.assert_not_awaited()
    bot_state_store.delete_state.assert_not_awaited()
    ctx.bot_state_store.fetch_field.assert_not_awaited()


# ---- on_fallback() ----

@pytest.mark.parametrize("state", [FirstTimeMappingState.IDLE, FirstTimeMappingState.WAITING_LANG])
@pytest.mark.parametrize("language", list(Language))
async def test_on_fallback_from_idle_or_waiting_lang_reasks_for_language(state, language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(state, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_fallback(ctx)

    assert message_store.send_message.await_args_list == [
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["fallback"]),
        call(sender=ctx.sender, to=ctx.recipient,
             message=_build_options_message(translations[language.name]["ask_for_lang_question"], _lang_options())),
    ]
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_LANG,
        bot_info={"fallback_count": "1"},
    )


@pytest.mark.parametrize("language", list(Language))
async def test_on_fallback_from_waiting_photo_reasks_for_photo(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_PHOTO, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_fallback(ctx)

    assert message_store.send_message.await_args_list == [
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["fallback"]),
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["ask_for_photo"]),
    ]
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_PHOTO,
        bot_info={"fallback_count": "1"},
    )


@pytest.mark.parametrize("language", list(Language))
async def test_on_fallback_from_waiting_coordinates_reasks_for_coordinates(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_COORDINATES, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_fallback(ctx)

    assert message_store.send_message.await_args_list == [
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["fallback"]),
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["ask_for_coordinate"]),
    ]
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_COORDINATES,
        bot_info={"fallback_count": "1"},
    )


@pytest.mark.parametrize("language", list(Language))
async def test_on_fallback_from_waiting_damage_level_reasks_for_damage_level(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_DAMAGE_LEVEL, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_fallback(ctx)

    assert message_store.send_message.await_args_list == [
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["fallback"]),
        call(sender=ctx.sender, to=ctx.recipient, message=_build_options_message(
            translations[language.name]["damage_level_question"], translations[language.name]["damage_level_options"]
        )),
    ]
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_DAMAGE_LEVEL,
        bot_info={"fallback_count": "1"},
    )


@pytest.mark.parametrize("language", list(Language))
async def test_on_fallback_from_mapping_completed_only_sends_the_fallback_message(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.MAPPING_COMPLETED, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_fallback(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["fallback"],
    )
    bot_state_store.save_state.assert_not_awaited()


@pytest.mark.parametrize("state, expected_message_key", [
    (FirstTimeMappingState.WAITING_PHOTO, "ask_for_photo"),
    (FirstTimeMappingState.WAITING_COORDINATES, "ask_for_coordinate"),
])
async def test_on_fallback_persists_the_incremented_count_on_top_of_a_prior_one(state, expected_message_key):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(state, Language.EN, bot_state_store, message_store)
    ctx = _ctx()
    ctx.bot_state_store.fetch_field.return_value = "2"

    await flow.on_fallback(ctx)

    ctx.bot_state_store.fetch_field.assert_awaited_once_with(bot_state_key=ctx.state_key, field="fallback_count")
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=state,
        bot_info={"fallback_count": "3"},
    )


@pytest.mark.parametrize("state", list(FirstTimeMappingState))
async def test_on_fallback_reaching_the_limit_shows_the_recovery_prompt(state):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(state, Language.EN, bot_state_store, message_store)
    ctx = _ctx()
    ctx.bot_state_store.fetch_field.return_value = "3"

    await flow.on_fallback(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(
            translations["EN"]["recovery_question"], translations["EN"]["recovery_options"]
        ),
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_RECOVERY_CHOICE,
        bot_info={"fallback_count": "4"},
    )


async def test_on_fallback_keeps_reshowing_the_recovery_prompt_once_past_the_limit():
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_RECOVERY_CHOICE, Language.EN, bot_state_store, message_store)
    ctx = _ctx()
    ctx.bot_state_store.fetch_field.return_value = "4"

    await flow.on_fallback(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(
            translations["EN"]["recovery_question"], translations["EN"]["recovery_options"]
        ),
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_RECOVERY_CHOICE,
        bot_info={"fallback_count": "5"},
    )


# ---- on_recovery_choice_answered() ----

@pytest.mark.parametrize("language", list(Language))
async def test_on_recovery_choice_answered_cancels_and_deletes_state(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_RECOVERY_CHOICE, language, bot_state_store, message_store)
    ctx = _ctx(answer="1")

    await flow.on_recovery_choice_answered(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["flow_cancelled"],
    )
    bot_state_store.delete_state.assert_awaited_once_with(bot_state_key=ctx.state_key)
    bot_state_store.save_state.assert_not_awaited()


@pytest.mark.parametrize("language", list(Language))
async def test_on_recovery_choice_answered_restarts_the_flow(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_RECOVERY_CHOICE, language, bot_state_store, message_store)
    ctx = _ctx(answer="2")

    await flow.on_recovery_choice_answered(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(translations[language.name]["ask_for_lang_question"], _lang_options()),
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_LANG,
        bot_info={"fallback_count": "0"},
    )
    bot_state_store.delete_state.assert_not_awaited()


async def test_on_recovery_choice_answered_reasks_for_an_invalid_option():
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_RECOVERY_CHOICE, Language.EN, bot_state_store, message_store)
    ctx = _ctx(answer="9")

    await flow.on_recovery_choice_answered(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=_build_options_message(translations["EN"]["recovery_question"], translations["EN"]["recovery_options"]),
    )
    bot_state_store.save_state.assert_not_awaited()
    bot_state_store.delete_state.assert_not_awaited()



# ---- messages the bot consumes as answers ----

async def test_answering_the_language_question_keeps_the_message_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_LANG,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )
    ctx = _ctx(answer="1", message_id="1786309661000-0")

    await flow.on_ask_for_lang(ctx)

    bot_consumed_messages_store.mark_consumed.assert_awaited_once_with(
        device=ctx.sender, message_id="1786309661000-0", occurred_at=OCCURRED_AT,
    )


async def test_an_invalid_language_answer_is_still_kept_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_LANG,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )

    await flow.on_ask_for_lang(_ctx(answer="no soy una opcion"))

    bot_consumed_messages_store.mark_consumed.assert_awaited_once()


async def test_the_text_that_opens_the_conversation_is_kept_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.IDLE,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )
    ctx = _ctx(answer="hola", message_id="1786309600000-0")

    await flow.on_ask_for_help(ctx)

    bot_consumed_messages_store.mark_consumed.assert_awaited_once_with(
        device=ctx.sender, message_id="1786309600000-0", occurred_at=OCCURRED_AT,
    )


async def test_answering_the_damage_level_question_keeps_the_message_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_DAMAGE_LEVEL,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )
    ctx_bot_state_store = AsyncMock(spec=BotStateStore)
    ctx_bot_state_store.fetch_field.return_value = "point-99"
    ctx = _ctx(answer="1", message_id="1786309700000-0", bot_state_store=ctx_bot_state_store)

    await flow.on_damage_level_answered(ctx)

    bot_consumed_messages_store.mark_consumed.assert_awaited_once_with(
        device=ctx.sender, message_id="1786309700000-0", occurred_at=OCCURRED_AT,
    )


async def test_an_invalid_damage_level_answer_is_still_kept_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_DAMAGE_LEVEL,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )

    await flow.on_damage_level_answered(_ctx(answer="no soy una opcion"))

    bot_consumed_messages_store.mark_consumed.assert_awaited_once()


@pytest.mark.parametrize("answer", ["1", "2", "no soy una opcion"])
async def test_answering_the_recovery_question_keeps_the_message_out_of_the_map(answer):
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_RECOVERY_CHOICE,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )
    ctx = _ctx(answer=answer, message_id="1786309800000-0")

    await flow.on_recovery_choice_answered(ctx)

    bot_consumed_messages_store.mark_consumed.assert_awaited_with(
        device=ctx.sender, message_id="1786309800000-0", occurred_at=OCCURRED_AT,
    )


async def test_a_message_without_text_reaching_on_ask_for_help_stays_available_to_the_map():
    # whatever arrives here carrying no text is content, not an answer
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.IDLE,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )

    await flow.on_ask_for_help(_ctx(answer=""))

    bot_consumed_messages_store.mark_consumed.assert_not_awaited()


@pytest.mark.parametrize("state, handler_name", [
    (FirstTimeMappingState.WAITING_PHOTO, "on_photo_uploaded"),
    (FirstTimeMappingState.WAITING_COORDINATES, "on_coordinates_sent"),
])
async def test_content_stays_available_to_the_map(state, handler_name):
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(state, bot_consumed_messages_store=bot_consumed_messages_store)

    await getattr(flow, handler_name)(_ctx())

    bot_consumed_messages_store.mark_consumed.assert_not_awaited()


@pytest.mark.parametrize("state", [
    FirstTimeMappingState.WAITING_PHOTO,
    FirstTimeMappingState.WAITING_COORDINATES,
    FirstTimeMappingState.MAPPING_COMPLETED,
])
async def test_a_message_that_only_hits_the_fallback_stays_available_to_the_map(state):
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(state, bot_consumed_messages_store=bot_consumed_messages_store)

    await flow.on_fallback(_ctx(answer="cualquier cosa"))

    bot_consumed_messages_store.mark_consumed.assert_not_awaited()
