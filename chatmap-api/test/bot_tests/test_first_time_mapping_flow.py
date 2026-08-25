from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from bot.configured_messages import BotConfiguredMessages, BotMaxAttemptsMessages, BotMessage, BotStep
from bot.flows.flow import BotFlowContext
from bot.flows.first_time_mapping.flow import FirstTimeMappingFlow, FirstTimeMappingState
from conversation_engine.event import EventName
from results.error import BotStateWithoutPointId, BotStateWithoutQuestion
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore

START = "Hi, I'm the ChatMap bot"
MEDIA = "Send the content"
MEDIA_ERROR = "That is not a photo"
LOCATION = "Now share the location"
LOCATION_ERROR = "That is not a location"
END = "Done, it is on the map"
NOTIFY = "Too many tries"
TO_RESTART = "restart"
TO_CANCEL = "cancel"
MAX_ATTEMPTS = 3

OCCURRED_AT = datetime(2026, 8, 9, 21, 7, 41, tzinfo=timezone.utc)


class _FakeSurveyStore:
    """
    Models the real store: appending an answer is what advances the cursor,
    so a question stops being returned once it has been answered.
    """

    def __init__(self, answered=None):
        self.answered = set(answered or [])
        self.added = []

    async def answered_question_ids(self, point_id: str) -> set[str]:
        return set(self.answered)

    async def add_response(self, point_id: str, question_id: str, question: str, answer: str) -> None:
        self.added.append({"point_id": point_id, "question_id": question_id, "question": question, "answer": answer})
        self.answered.add(question_id)


def _question(item_id="q-1", prompt="Main material?", options=None, error_message="Pick one of the options"):
    return BotMessage(
        id=item_id, bot_step=BotStep.SINGLE_CHOICE, prompt=prompt,
        error_message=error_message, options=options if options is not None else ["Bricks", "Wood"],
    )


def _conversation(questions=(), max_attempts_quantity=MAX_ATTEMPTS):
    return BotConfiguredMessages(
        max_attempts_messages=BotMaxAttemptsMessages(
            max_attempts_quantity=max_attempts_quantity,
            notify_message=NOTIFY, to_restart=TO_RESTART, to_cancel=TO_CANCEL,
        ),
        messages=[
            BotMessage(id="start-1", bot_step=BotStep.START, prompt=START, error_message=""),
            BotMessage(id="media-1", bot_step=BotStep.MEDIA, prompt=MEDIA, error_message=MEDIA_ERROR),
            BotMessage(id="location-1", bot_step=BotStep.LOCATION, prompt=LOCATION, error_message=LOCATION_ERROR),
            BotMessage(id="end-1", bot_step=BotStep.END, prompt=END, error_message=""),
        ] + list(questions),
    )


def _make_flow(state, bot_state_store=None, message_to_send_store=None,
               survey_responses_store=None, bot_consumed_messages_store=None):
    if bot_state_store is None:
        bot_state_store = AsyncMock(spec=BotStateStore)
        bot_state_store.fetch_fallback_count.return_value = 0

    return FirstTimeMappingFlow(
        state=state,
        bot_state_store=bot_state_store,
        message_to_send_store=message_to_send_store or AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=bot_consumed_messages_store or AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=survey_responses_store or _FakeSurveyStore(),
    )


def _ctx(configured_messages=None, **overrides):
    fields = dict(
        state_key="key-1", recipient="user-enc-1", sender="device-1", answer="", message_id="msg-1",
        occurred_at=OCCURRED_AT, point_id=None, configured_messages=configured_messages or _conversation(),
    )
    fields.update(overrides)
    return BotFlowContext(**fields)


def _sent(message_to_send_store):
    sent = []
    for call in message_to_send_store.send_message.await_args_list:
        messages = call.kwargs["messages"]
        sent.extend([messages] if isinstance(messages, str) else list(messages))
    return sent


def _saved_state(bot_state_store):
    return bot_state_store.save_state.await_args.kwargs


# ---- helpers ----

def test_options_are_numbered_for_the_user():
    assert BotConfiguredMessages.build_options_message("Material?", ["Bricks", "Wood"]) == \
           "Material?\n\n1️⃣ Bricks\n2️⃣ Wood"


def test_the_tenth_option_still_gets_a_keycap():
    message = BotConfiguredMessages.build_options_message("Pick", [f"Option {i}" for i in range(1, 11)])

    assert message.endswith("🔟 Option 10")


@pytest.mark.parametrize("answer, expected", [
    ("1", "Bricks"), ("2", "Wood"), (" 2 ", "Wood"),
    ("0", None), ("3", None), ("", None), ("bricks", None), (None, None),
])
def test_only_a_valid_option_number_selects_a_label(answer, expected):
    assert BotConfiguredMessages.selected_option(answer, ["Bricks", "Wood"]) == expected


# ---- create() ----

async def test_create_defaults_to_idle_when_no_state_stored():
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_state.return_value = {}

    flow = await FirstTimeMappingFlow.create(
        bot_state_key="key-1",
        bot_state_store=bot_state_store,
        message_to_send_store=AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=_FakeSurveyStore(),
    )

    assert flow.state == FirstTimeMappingState.IDLE
    bot_state_store.fetch_state.assert_awaited_once_with(bot_state_key="key-1")


@pytest.mark.parametrize("stored_state, expected", [
    ("WAITING_PHOTO", FirstTimeMappingState.WAITING_PHOTO),
    ("WAITING_COORDINATES", FirstTimeMappingState.WAITING_COORDINATES),
    ("WAITING_SURVEY_ANSWER", FirstTimeMappingState.WAITING_SURVEY_ANSWER),
    ("WAITING_RECOVERY_CHOICE", FirstTimeMappingState.WAITING_RECOVERY_CHOICE),
    ("NOT_A_REAL_STATE", FirstTimeMappingState.IDLE),
])
async def test_create_restores_the_stored_state(stored_state, expected):
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_state.return_value = {"state": stored_state}

    flow = await FirstTimeMappingFlow.create(
        bot_state_key="key-1",
        bot_state_store=bot_state_store,
        message_to_send_store=AsyncMock(spec=MessageToSendStore),
        bot_consumed_messages_store=AsyncMock(spec=BotConsumedMessagesStore),
        survey_responses_store=_FakeSurveyStore(),
    )

    assert flow.state == expected


# ---- start ----

async def test_start_greets_and_asks_for_the_media_in_one_turn():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.IDLE, bot_state_store=bot_state_store,
                      message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_SEND_TEXT, context=_ctx())

    assert _sent(message_to_send_store) == [START, MEDIA]
    assert _saved_state(bot_state_store)["state"] == FirstTimeMappingState.WAITING_PHOTO


async def test_an_unexpected_first_event_starts_the_conversation_too():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    flow = _make_flow(FirstTimeMappingState.IDLE, message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_UPLOAD_PHOTO, context=_ctx())

    assert _sent(message_to_send_store) == [START, MEDIA]


# ---- media and location ----

async def test_a_photo_moves_on_to_the_location_question():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_PHOTO, bot_state_store=bot_state_store,
                      message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_UPLOAD_PHOTO, context=_ctx())

    assert _sent(message_to_send_store) == [LOCATION]
    assert _saved_state(bot_state_store)["state"] == FirstTimeMappingState.WAITING_COORDINATES


# ---- the survey ----

async def test_coordinates_ask_the_first_configured_question():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    conversation = _conversation([_question("q-1"), _question("q-2", prompt="Second?")])
    flow = _make_flow(
        FirstTimeMappingState.WAITING_COORDINATES,
        bot_state_store=bot_state_store, message_to_send_store=message_to_send_store,
    )

    await flow.call(current_event=EventName.USER_SEND_COORDINATES,
                    context=_ctx(configured_messages=conversation, point_id="point-1"))

    assert _sent(message_to_send_store) == ["Main material?\n\n1️⃣ Bricks\n2️⃣ Wood"]
    saved = _saved_state(bot_state_store)
    assert saved["state"] == FirstTimeMappingState.WAITING_SURVEY_ANSWER
    assert saved["bot_info"]["point_id"] == "point-1"


async def test_coordinates_end_the_flow_when_no_question_is_configured():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_COORDINATES, bot_state_store=bot_state_store,
                      message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_SEND_COORDINATES, context=_ctx(point_id="point-1"))

    assert _sent(message_to_send_store) == [END]
    assert _saved_state(bot_state_store)["state"] == FirstTimeMappingState.MAPPING_COMPLETED
    bot_state_store.delete_state.assert_awaited_once_with(bot_state_key="key-1")


async def test_coordinates_without_a_point_id_are_rejected():
    flow = _make_flow(FirstTimeMappingState.WAITING_COORDINATES)

    with pytest.raises(BotStateWithoutPointId):
        await flow.call(current_event=EventName.USER_SEND_COORDINATES, context=_ctx(point_id=None))


async def test_a_valid_answer_is_recorded_and_the_next_question_asked():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    survey = _FakeSurveyStore()
    conversation = _conversation([_question("q-1"), _question("q-2", prompt="Second?", options=["Yes", "No"])])
    flow = _make_flow(
        FirstTimeMappingState.WAITING_SURVEY_ANSWER,
        message_to_send_store=message_to_send_store, survey_responses_store=survey,
    )

    await flow.call(current_event=EventName.USER_SEND_TEXT,
                    context=_ctx(configured_messages=conversation, point_id="point-1", answer="2"))

    assert survey.added == [
        {"point_id": "point-1", "question_id": "q-1", "question": "Main material?", "answer": "Wood"}
    ]
    assert _sent(message_to_send_store) == ["Second?\n\n1️⃣ Yes\n2️⃣ No"]


async def test_answering_the_last_question_ends_the_flow():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    survey = _FakeSurveyStore()
    conversation = _conversation([_question("q-1")])
    flow = _make_flow(
        FirstTimeMappingState.WAITING_SURVEY_ANSWER,
        bot_state_store=bot_state_store, message_to_send_store=message_to_send_store, survey_responses_store=survey,
    )

    await flow.call(current_event=EventName.USER_SEND_TEXT,
                    context=_ctx(configured_messages=conversation, point_id="point-1", answer="1"))

    assert survey.added[0]["answer"] == "Bricks"
    assert _sent(message_to_send_store) == [END]
    assert _saved_state(bot_state_store)["state"] == FirstTimeMappingState.MAPPING_COMPLETED
    bot_state_store.delete_state.assert_awaited_once()


async def test_an_already_answered_question_is_not_asked_again():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    survey = _FakeSurveyStore(answered={"q-1"})
    conversation = _conversation([_question("q-1"), _question("q-2", prompt="Second?", options=["Yes", "No"])])
    flow = _make_flow(
        FirstTimeMappingState.WAITING_SURVEY_ANSWER,
        message_to_send_store=message_to_send_store, survey_responses_store=survey,
    )

    await flow.call(current_event=EventName.USER_SEND_TEXT,
                    context=_ctx(configured_messages=conversation, point_id="point-1", answer="1"))

    assert survey.added[0]["question_id"] == "q-2"
    assert survey.added[0]["answer"] == "Yes"


async def test_an_invalid_answer_re_asks_without_recording_anything():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    survey = _FakeSurveyStore()
    conversation = _conversation([_question("q-1")])
    flow = _make_flow(
        FirstTimeMappingState.WAITING_SURVEY_ANSWER,
        bot_state_store=bot_state_store, message_to_send_store=message_to_send_store, survey_responses_store=survey,
    )

    await flow.call(current_event=EventName.USER_SEND_TEXT,
                    context=_ctx(configured_messages=conversation, point_id="point-1", answer="9"))

    assert survey.added == []
    assert _sent(message_to_send_store) == ["Pick one of the options", "Main material?\n\n1️⃣ Bricks\n2️⃣ Wood"]
    bot_state_store.save_state.assert_not_awaited()


async def test_deleting_every_question_mid_survey_raises():
    flow = _make_flow(FirstTimeMappingState.WAITING_SURVEY_ANSWER)

    with pytest.raises(BotStateWithoutQuestion):
        await flow.call(current_event=EventName.USER_SEND_TEXT,
                        context=_ctx(point_id="point-1", answer="1"))


async def test_a_survey_answer_without_a_point_id_is_rejected():
    conversation = _conversation([_question("q-1")])
    flow = _make_flow(FirstTimeMappingState.WAITING_SURVEY_ANSWER)

    with pytest.raises(BotStateWithoutPointId):
        await flow.call(current_event=EventName.USER_SEND_TEXT,
                        context=_ctx(configured_messages=conversation, answer="1"))


# ---- fallback ----

@pytest.mark.parametrize("state, expected_error, expected_prompt", [
    (FirstTimeMappingState.WAITING_PHOTO, MEDIA_ERROR, MEDIA),
    (FirstTimeMappingState.WAITING_COORDINATES, LOCATION_ERROR, LOCATION),
])
async def test_a_wrong_reply_sends_that_step_error_and_asks_again(state, expected_error, expected_prompt):
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_fallback_count.return_value = 0
    flow = _make_flow(state, bot_state_store=bot_state_store, message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_SEND_TEXT, context=_ctx())

    assert _sent(message_to_send_store) == [expected_error, expected_prompt]
    bot_state_store.increment_fallback_count.assert_awaited_once_with(bot_state_key="key-1")


async def test_a_wrong_reply_during_the_survey_re_asks_the_current_question():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    conversation = _conversation([_question("q-1")])
    flow = _make_flow(FirstTimeMappingState.WAITING_SURVEY_ANSWER, message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_UPLOAD_PHOTO,
                    context=_ctx(configured_messages=conversation, point_id="point-1"))

    assert _sent(message_to_send_store) == ["Pick one of the options", "Main material?\n\n1️⃣ Bricks\n2️⃣ Wood"]


async def test_the_fallback_count_keeps_growing():
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_fallback_count.return_value = 2
    flow = _make_flow(FirstTimeMappingState.WAITING_PHOTO, bot_state_store=bot_state_store)

    await flow.call(current_event=EventName.USER_SEND_TEXT, context=_ctx())

    bot_state_store.increment_fallback_count.assert_awaited_once_with(bot_state_key="key-1")


async def test_crossing_the_fallback_limit_offers_cancel_or_restart():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    bot_state_store.fetch_fallback_count.return_value = MAX_ATTEMPTS + 1
    flow = _make_flow(FirstTimeMappingState.WAITING_PHOTO, bot_state_store=bot_state_store,
                      message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_SEND_TEXT, context=_ctx())

    assert _sent(message_to_send_store) == [f"{NOTIFY} {TO_CANCEL}, {TO_RESTART}"]
    assert _saved_state(bot_state_store)["state"] == FirstTimeMappingState.WAITING_RECOVERY_CHOICE
    bot_state_store.increment_fallback_count.assert_not_awaited()


# ---- recovery ----

async def test_choosing_cancel_drops_the_state_without_a_goodbye():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_RECOVERY_CHOICE, bot_state_store=bot_state_store,
                      message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_SEND_TEXT, context=_ctx(answer=TO_CANCEL))

    message_to_send_store.send_message.assert_not_awaited()
    bot_state_store.delete_state.assert_awaited_once_with(bot_state_key="key-1")
    bot_state_store.save_state.assert_not_awaited()


async def test_choosing_restart_greets_again():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_RECOVERY_CHOICE, bot_state_store=bot_state_store,
                      message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_SEND_TEXT, context=_ctx(answer=TO_RESTART))

    assert _sent(message_to_send_store) == [START, MEDIA]
    assert _saved_state(bot_state_store)["state"] == FirstTimeMappingState.WAITING_PHOTO


async def test_an_invalid_recovery_answer_re_asks_without_saving():
    message_to_send_store = AsyncMock(spec=MessageToSendStore)
    bot_state_store = AsyncMock(spec=BotStateStore)
    flow = _make_flow(FirstTimeMappingState.WAITING_RECOVERY_CHOICE, bot_state_store=bot_state_store,
                      message_to_send_store=message_to_send_store)

    await flow.call(current_event=EventName.USER_SEND_TEXT, context=_ctx(answer="not a valid choice"))

    assert _sent(message_to_send_store) == [f"{NOTIFY} {TO_CANCEL}, {TO_RESTART}"]
    bot_state_store.save_state.assert_not_awaited()
    bot_state_store.delete_state.assert_not_awaited()


# ---- messages the bot consumes as answers ----

async def test_the_text_that_opens_the_conversation_is_kept_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.IDLE,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )
    ctx = _ctx(answer="hola", message_id="1786309600000-0")

    await flow.on_start(ctx)

    bot_consumed_messages_store.mark_consumed.assert_awaited_once_with(
        device=ctx.sender, message_id="1786309600000-0", occurred_at=OCCURRED_AT,
    )


async def test_a_message_without_text_reaching_on_start_stays_available_to_the_map():
    # whatever arrives here carrying no text is content, not an answer
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.IDLE,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )

    await flow.on_start(_ctx(answer=""))

    bot_consumed_messages_store.mark_consumed.assert_not_awaited()


async def test_answering_the_survey_keeps_the_message_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    conversation = _conversation([_question()])
    flow = _make_flow(
        FirstTimeMappingState.WAITING_SURVEY_ANSWER,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )
    ctx = _ctx(configured_messages=conversation, point_id="point-99", answer="1", message_id="1786309700000-0")

    await flow.on_survey_answered(ctx)

    bot_consumed_messages_store.mark_consumed.assert_awaited_once_with(
        device=ctx.sender, message_id="1786309700000-0", occurred_at=OCCURRED_AT,
    )


async def test_an_invalid_survey_answer_is_still_kept_out_of_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    conversation = _conversation([_question()])
    flow = _make_flow(
        FirstTimeMappingState.WAITING_SURVEY_ANSWER,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )

    await flow.on_survey_answered(
        _ctx(configured_messages=conversation, point_id="point-99", answer="no soy una opcion")
    )

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


async def test_the_photo_stays_available_to_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_PHOTO,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )

    await flow.on_photo_uploaded(_ctx())

    bot_consumed_messages_store.mark_consumed.assert_not_awaited()


async def test_the_location_stays_available_to_the_map():
    bot_consumed_messages_store = AsyncMock(spec=BotConsumedMessagesStore)
    flow = _make_flow(
        FirstTimeMappingState.WAITING_COORDINATES,
        bot_consumed_messages_store=bot_consumed_messages_store,
    )

    await flow.on_coordinates_sent(_ctx(point_id="point-42"))

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
