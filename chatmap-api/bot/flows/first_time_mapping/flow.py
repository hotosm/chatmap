import logging

from bot.configured_messages import BotConfiguredMessages
from bot.flows.flow import BotFlow, BotTransitions, BotFlowContext, not_handler_created
from conversation_engine.event import EventName
from enum import Enum, auto
from results.error import BotStateWithoutPointId, BotStateWithoutQuestion
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_configured_messages_store import BotStep
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore
from store.survey_responses_store import SurveyResponsesStore

logger = logging.getLogger(__name__)


class FirstTimeMappingState(Enum):
    IDLE = auto()
    WAITING_FOR_DATA_MAPPING = auto()
    WAITING_COORDINATES = auto()
    WAITING_SURVEY_ANSWER = auto()
    WAITING_RECOVERY_CHOICE = auto()
    MAPPING_COMPLETED = auto()


class FirstTimeMappingFlow(BotFlow):
    name = "first_time_mapping_flow"

    @classmethod
    async def create(
            cls,
            bot_state_key: str,
            bot_state_store: BotStateStore,
            message_to_send_store: MessageToSendStore,
            bot_consumed_messages_store: BotConsumedMessagesStore,
            survey_responses_store: SurveyResponsesStore
    ):
        result = await bot_state_store.fetch_state(bot_state_key=bot_state_key)

        if result:
            raw_state = result.get("state")
            state = FirstTimeMappingState.__members__.get(raw_state, FirstTimeMappingState.IDLE) if isinstance(
                raw_state, str) else FirstTimeMappingState.IDLE
        else:
            state = FirstTimeMappingState.IDLE

        return cls(
            state=state,
            bot_state_store=bot_state_store,
            message_to_send_store=message_to_send_store,
            bot_consumed_messages_store=bot_consumed_messages_store,
            survey_responses_store=survey_responses_store
        )

    async def call(self, current_event: EventName, context: BotFlowContext) -> None:
        logger.info(f"Calling bot flow: '{self.name}' with state: '{self.state}' for event: '{current_event}'")

        handler = self.transitions.get((self.state, current_event))

        if handler:
            await handler(self, context)
        else:
            not_handler_created(self.name, self.state, current_event)
            await self.on_fallback(ctx=context)

    async def on_start(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_start")

        # The text was consumed to open the conversation -- the user got a
        # greeting, not a mapped point -- so it must not reach the map.
        # Guarded on text so that anything reaching this handler without text
        # is treated as content and stays available to the map.
        if ctx.answer:
            await self.bot_consumed_messages_store.mark_consumed(
                device=ctx.sender, message_id=ctx.message_id, occurred_at=ctx.occurred_at
            )

        await self.message_to_send_store.send_message(
            sender=ctx.sender,
            to=ctx.recipient,
            messages=[
                ctx.configured_messages.text_of(BotStep.START),
                ctx.configured_messages.text_of(BotStep.MEDIA),
            ]
        )

        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.WAITING_FOR_DATA_MAPPING,
        )

    async def on_data_uploaded(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_data_uploaded")

        await self.message_to_send_store.send_message(
            sender=ctx.sender,
            to=ctx.recipient,
            messages=[ctx.configured_messages.text_of(BotStep.LOCATION)]
        )

        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.WAITING_COORDINATES,
        )

    async def on_coordinates_sent(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_coordinates_sent")

        if not ctx.point_id:
            logger.error(f"Coordinates for state: '{ctx.state_key}' arrived without a point id")
            raise BotStateWithoutPointId(message_id=ctx.message_id)

        if ctx.configured_messages.has_survey_questions():
            answered = await self.survey_responses_store.answered_question_ids(map_id=ctx.map_id, point_id=ctx.point_id)
            question = ctx.configured_messages.next_question_to_answer(answered)

            if question:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender,
                    to=ctx.recipient,
                    messages=[
                        BotConfiguredMessages.build_options_message(question.prompt, question.options)
                    ]
                )
                await self.bot_state_store.save_state(
                    bot_state_key=ctx.state_key,
                    state=FirstTimeMappingState.WAITING_SURVEY_ANSWER,
                    bot_info={"point_id": ctx.point_id}
                )

                return

        await self.message_to_send_store.send_message(
            sender=ctx.sender,
            to=ctx.recipient,
            messages=[ctx.configured_messages.text_of(BotStep.END)]
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.MAPPING_COMPLETED,
        )

        logger.info("bot flow end, deleting state...")
        await self.bot_state_store.delete_state(bot_state_key=ctx.state_key)

    async def on_survey_answered(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_survey_answered")

        if await self.bot_consumed_messages_store.is_consumed(device=ctx.sender, message_id=ctx.message_id):
            logger.info(f"Message '{ctx.message_id}' already handled by the bot, skipping")
            return

        await self.bot_consumed_messages_store.mark_consumed(
            device=ctx.sender, message_id=ctx.message_id, occurred_at=ctx.occurred_at
        )

        if not ctx.point_id:
            logger.error(f"Coordinates for state: '{ctx.state_key}' arrived without a point id")
            raise BotStateWithoutPointId(message_id=ctx.message_id)

        answered = await self.survey_responses_store.answered_question_ids(map_id=ctx.map_id, point_id=ctx.point_id)
        current_question = ctx.configured_messages.next_question_to_answer(answered)

        if not current_question:
            logger.error(f"Survey answer for state: '{ctx.state_key}' arrived without a pending question")
            raise BotStateWithoutQuestion(message_id=ctx.message_id)

        if current_question.bot_step == BotStep.FREE_TEXT:
            answer = ctx.answer
        else:
            answer = BotConfiguredMessages.selected_option(ctx.answer, current_question.options)

            if answer is None:
                logger.info(f"Invalid survey option received: '{ctx.answer}', re-asking...")
                await self.on_fallback(ctx)
                return

        logger.info("storing survey response...")
        await self.survey_responses_store.add_response(
            map_id=ctx.map_id,
            point_id=ctx.point_id,
            question_id=current_question.id,
            question=current_question.prompt,
            answer=answer
        )

        answered = await self.survey_responses_store.answered_question_ids(map_id=ctx.map_id, point_id=ctx.point_id)
        next_question = ctx.configured_messages.next_question_to_answer(answered)

        if next_question:
            await self.message_to_send_store.send_message(
                sender=ctx.sender,
                to=ctx.recipient,
                messages=[
                    BotConfiguredMessages.build_options_message(next_question.prompt, next_question.options)
                ]
            )
            await self.bot_state_store.save_state(
                bot_state_key=ctx.state_key,
                state=FirstTimeMappingState.WAITING_SURVEY_ANSWER,
                bot_info={"point_id": ctx.point_id}
            )

            return

        await self.message_to_send_store.send_message(
            sender=ctx.sender,
            to=ctx.recipient,
            messages=[ctx.configured_messages.text_of(BotStep.END)]
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.MAPPING_COMPLETED,
        )

        logger.info("bot flow end, deleting state...")
        await self.bot_state_store.delete_state(bot_state_key=ctx.state_key)

    async def on_recovery_choice_answered(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_recovery_choice_answered")

        if await self.bot_consumed_messages_store.is_consumed(device=ctx.sender, message_id=ctx.message_id):
            logger.info(f"Message '{ctx.message_id}' already handled by the bot, skipping")
            return

        await self.bot_consumed_messages_store.mark_consumed(
            device=ctx.sender, message_id=ctx.message_id, occurred_at=ctx.occurred_at
        )

        answer = (ctx.answer or "").strip().lower()
        to_cancel = ctx.configured_messages.max_attempts_messages.to_cancel.strip().lower()
        to_restart = ctx.configured_messages.max_attempts_messages.to_restart.strip().lower()

        if answer not in (to_cancel, to_restart):
            logger.info(f"Invalid recovery option received: '{ctx.answer}', re-asking...")

            notify_message = ctx.configured_messages.max_attempts_messages.full_message()

            await self.message_to_send_store.send_message(
                sender=ctx.sender,
                to=ctx.recipient,
                messages=[notify_message]
            )
            return

        if answer == to_cancel:
            if ctx.point_id:
                await self.survey_responses_store.delete_responses(map_id=ctx.map_id, point_id=ctx.point_id)
            await self.bot_state_store.delete_state(bot_state_key=ctx.state_key)
            return

        logger.info("user chose to restart the flow...")
        await self.on_start(ctx)

    async def on_fallback(self, ctx: BotFlowContext) -> None:
        fallback_count = await self.bot_state_store.fetch_fallback_count(bot_state_key=ctx.state_key)

        if fallback_count >= ctx.configured_messages.max_attempts_messages.max_attempts_quantity:
            logger.info("fallback limit reached, offering cancel/restart...")

            notify_message = ctx.configured_messages.max_attempts_messages.full_message()

            await self.message_to_send_store.send_message(
                sender=ctx.sender,
                to=ctx.recipient,
                messages=[notify_message]
            )

            await self.bot_state_store.save_state(
                bot_state_key=ctx.state_key,
                state=FirstTimeMappingState.WAITING_RECOVERY_CHOICE,
                reset_fallback_count=False,
            )
            return

        match self.state:
            case FirstTimeMappingState.IDLE:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender,
                    to=ctx.recipient,
                    messages=[
                        ctx.configured_messages.text_of(BotStep.START),
                        ctx.configured_messages.text_of(BotStep.MEDIA),
                    ]
                )
            case FirstTimeMappingState.WAITING_FOR_DATA_MAPPING:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender,
                    to=ctx.recipient,
                    messages=[
                        ctx.configured_messages.error_of(BotStep.MEDIA),
                        ctx.configured_messages.text_of(BotStep.MEDIA),
                    ]
                )

            case FirstTimeMappingState.WAITING_COORDINATES:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender,
                    to=ctx.recipient,
                    messages=[
                        ctx.configured_messages.error_of(BotStep.LOCATION),
                        ctx.configured_messages.text_of(BotStep.LOCATION),
                    ]
                )

            case FirstTimeMappingState.WAITING_SURVEY_ANSWER:

                if not ctx.point_id:
                    logger.error(f"Coordinates for state: '{ctx.state_key}' arrived without a point id")
                    raise BotStateWithoutPointId(message_id=ctx.message_id)

                answered = await self.survey_responses_store.answered_question_ids(map_id=ctx.map_id,
                                                                                   point_id=ctx.point_id)
                question = ctx.configured_messages.next_question_to_answer(answered)

                if not question:
                    logger.error(f"Survey fallback for state: '{ctx.state_key}' arrived without a pending question")
                    raise BotStateWithoutQuestion(message_id=ctx.message_id)

                await self.message_to_send_store.send_message(
                    sender=ctx.sender,
                    to=ctx.recipient,
                    messages=[
                        question.error_message,
                        BotConfiguredMessages.build_options_message(question.prompt, question.options)
                    ]
                )

        await self.bot_state_store.increment_fallback_count(bot_state_key=ctx.state_key)
        return

    transitions: BotTransitions = {
        (FirstTimeMappingState.IDLE, EventName.USER_SEND_TEXT): on_start,
        (FirstTimeMappingState.WAITING_FOR_DATA_MAPPING, EventName.USER_UPLOAD_PHOTO): on_data_uploaded,
        (FirstTimeMappingState.WAITING_FOR_DATA_MAPPING, EventName.USER_UPLOAD_VIDEO): on_data_uploaded,
        (FirstTimeMappingState.WAITING_FOR_DATA_MAPPING, EventName.USER_UPLOAD_AUDIO): on_data_uploaded,
        (FirstTimeMappingState.WAITING_COORDINATES, EventName.USER_SEND_COORDINATES): on_coordinates_sent,
        (FirstTimeMappingState.WAITING_SURVEY_ANSWER, EventName.USER_SEND_TEXT): on_survey_answered,
        (FirstTimeMappingState.WAITING_RECOVERY_CHOICE, EventName.USER_SEND_TEXT): on_recovery_choice_answered,
    }
