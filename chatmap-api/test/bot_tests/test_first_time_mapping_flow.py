from datetime import datetime, timezone
from unittest.mock import AsyncMock, call, patch

import pytest

from bot.flow import BotFlowContext, Language
from bot.flows.first_time_mapping import flow as flow_module
from bot.flows.first_time_mapping.flow import (
    FirstTimeMappingFlow,
    FirstTimeMappingState,
    translations,
)
from conversation_engine.event import EventName
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore


OCCURRED_AT = datetime(2026, 8, 9, 21, 7, 41, tzinfo=timezone.utc)


def _make_flow(state, language=Language.ES, bot_state_store=None, message_to_send_store=None,
               bot_consumed_messages_store=None):
    return FirstTimeMappingFlow(
        state=state,
        language=language,
        bot_state_store=bot_state_store or AsyncMock(spec=BotStateStore),
        message_to_send_store=message_to_send_store or AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=bot_consumed_messages_store or AsyncMock(spec=BotConsumedMessagesStore),
    )


def _ctx(**overrides):
    fields = dict(
        state_key="key-1", recipient="user-enc-1", sender="device-1", answer="",
        message_id="msg-1", occurred_at=OCCURRED_AT,
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
    )

    assert flow.state == FirstTimeMappingState.IDLE
    assert flow.language == Language.default()
    bot_state_store.fetch_state.assert_awaited_once_with(bot_state_key="key-1")


@pytest.mark.parametrize("stored_state, stored_lang, expected_state, expected_lang", [
    ("WAITING_LANG", "ES", FirstTimeMappingState.WAITING_LANG, Language.ES),
    ("WAITING_PHOTO", "EN", FirstTimeMappingState.WAITING_PHOTO, Language.EN),
    ("WAITING_COORDINATES", "PT", FirstTimeMappingState.WAITING_COORDINATES, Language.PT),
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
    )

    assert flow.state == FirstTimeMappingState.WAITING_PHOTO
    assert flow.language == Language.default()


# ---- transitions table wiring ----

@pytest.mark.parametrize("state, event, handler_name", [
    (FirstTimeMappingState.IDLE, EventName.USER_SEND_TEXT, "on_ask_for_help"),
    (FirstTimeMappingState.WAITING_LANG, EventName.USER_SEND_TEXT, "on_ask_for_lang"),
    (FirstTimeMappingState.WAITING_PHOTO, EventName.USER_UPLOAD_PHOTO, "on_photo_uploaded"),
    (FirstTimeMappingState.WAITING_COORDINATES, EventName.USER_SEND_COORDINATES, "on_coordinates_sent"),
])
def test_transitions_table_wiring(state, event, handler_name):
    assert FirstTimeMappingFlow.transitions[(state, event)] is getattr(FirstTimeMappingFlow, handler_name)


def test_transitions_table_has_no_unexpected_entries():
    assert len(FirstTimeMappingFlow.transitions) == 4


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
        message=translations[language.name]["ask_for_lang"],
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_LANG,
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
        bot_info={"lang": expected_language.name},
    )


async def test_on_ask_for_lang_reasks_in_current_language_for_an_invalid_option():
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_LANG, Language.EN, bot_state_store, message_store)
    ctx = _ctx(answer="9")

    await flow.on_ask_for_lang(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=translations["EN"]["ask_for_lang"],
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
    )


@pytest.mark.parametrize("language", list(Language))
async def test_on_coordinates_sent_completes_the_flow_and_clears_state(language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_COORDINATES, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_coordinates_sent(ctx)

    message_store.send_message.assert_awaited_once_with(
        sender=ctx.sender, to=ctx.recipient,
        message=translations[language.name]["end_flow"],
    )
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.MAPPING_COMPLETED,
    )
    bot_state_store.delete_state.assert_awaited_once_with(bot_state_key=ctx.state_key)
    assert [call[0] for call in bot_state_store.method_calls] == ["save_state", "delete_state"]


# ---- on_fallback() ----

@pytest.mark.parametrize("state", [FirstTimeMappingState.IDLE, FirstTimeMappingState.WAITING_LANG])
@pytest.mark.parametrize("language", list(Language))
async def test_on_fallback_from_idle_or_waiting_lang_delegates_to_on_ask_for_help(state, language):
    message_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(state, language, bot_state_store, message_store)
    ctx = _ctx()

    await flow.on_fallback(ctx)

    assert message_store.send_message.await_args_list == [
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["fallback"]),
        call(sender=ctx.sender, to=ctx.recipient, message=translations[language.name]["ask_for_lang"]),
    ]
    bot_state_store.save_state.assert_awaited_once_with(
        bot_state_key=ctx.state_key, state=FirstTimeMappingState.WAITING_LANG,
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
    bot_state_store.save_state.assert_not_awaited()


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
    bot_state_store.save_state.assert_not_awaited()


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


@pytest.mark.parametrize("state", [FirstTimeMappingState.IDLE, FirstTimeMappingState.WAITING_LANG])
async def test_a_photo_or_location_routed_through_on_ask_for_help_stays_available_to_the_map(state):
    # on_fallback delegates to on_ask_for_help in these states, and what
    # arrives there is content: it carries no text
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(state, bot_consumed_messages_store=bot_consumed_messages_store)

    await flow.on_fallback(_ctx(answer=""))

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
