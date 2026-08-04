from bot.flow import BotFlow, BotTransitions, BotFlowContext, not_handler_created, Language
from conversation_engine.event import EventName
from enum import Enum, auto

from results.error import BotStateWithoutPointId
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore
from store.survey_responses_store import SurveyResponsesStore

from pathlib import Path
import json

import logging

logger = logging.getLogger(__name__)

_MESSAGES_PATH = Path(__file__).parent / "messages.json"

FALLBACK_LIMIT = 3

with open(_MESSAGES_PATH, encoding="utf-8") as f:
    translations = json.load(f)


def _build_options_message(question: str, options: dict[str, str]) -> str:
    options_text = "\n".join(f"{code}️⃣ {label}" for code, label in options.items())
    return f"{question}\n\n{options_text}"


def _lang_options() -> dict[str, str]:
    return {str(i): lang.value for i, lang in enumerate(Language, start=1)}


class FirstTimeMappingState(Enum):
    IDLE = auto()
    WAITING_LANG = auto()
    WAITING_PHOTO = auto()
    WAITING_COORDINATES = auto()
    WAITING_DAMAGE_LEVEL = auto()
    MAPPING_COMPLETED = auto()
    WAITING_RECOVERY_CHOICE = auto()


class FirstTimeMappingFlow(BotFlow):
    name = "first_time_mapping_flow"

    @classmethod
    async def create(
            cls,
            bot_state_key: str,
            bot_state_store: BotStateStore,
            message_to_send_store: MessageToSendStore,
            survey_responses_store: SurveyResponsesStore
    ):
        result = await bot_state_store.fetch_state(bot_state_key=bot_state_key)

        if result:
            raw_state = result.get("state")
            state = FirstTimeMappingState.__members__.get(raw_state, FirstTimeMappingState.IDLE) if isinstance(
                raw_state, str) else FirstTimeMappingState.IDLE

            raw_language = result.get("lang")
            language = Language.__members__.get(raw_language, Language.default()) if isinstance(raw_language,
                                                                                                str) else Language.default()
        else:
            state = FirstTimeMappingState.IDLE
            language = Language.default()

        return cls(
            state=state, language=language,
            bot_state_store=bot_state_store,
            message_to_send_store=message_to_send_store,
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

    async def on_ask_for_help(
            self,
            ctx: BotFlowContext,
    ) -> None:
        logger.info("Handling: on_ask_for_help")
        logger.info("sending message...")

        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=_build_options_message(translations[self.language.name]["ask_for_lang_question"], _lang_options())
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.WAITING_LANG,
            bot_info={"fallback_count": "0"}
        )

    async def on_ask_for_lang(
            self,
            ctx: BotFlowContext,
    ) -> None:
        logger.info("Handling: on_ask_for_lang")

        selected_language = ctx.answer
        displayed_options = {str(i): lang.name for i, lang in enumerate(Language, start=1)}

        if selected_language not in displayed_options:
            logger.info(f"Invalid language option received: '{selected_language}', re-asking...")

            await self.message_to_send_store.send_message(
                sender=ctx.sender, to=ctx.recipient,
                message=_build_options_message(translations[self.language.name]["ask_for_lang_question"],
                                               _lang_options())
            )
            return

        language_key = displayed_options[selected_language]

        logger.info("sending message...")
        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=translations[language_key]["ask_for_photo"]
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.WAITING_PHOTO,
            bot_info={"lang": language_key, "fallback_count": "0"}
        )

    async def on_photo_uploaded(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_ask_for_help")
        logger.info("sending message...")

        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=translations[self.language.name]["ask_for_coordinate"]
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.WAITING_COORDINATES,
            bot_info={"fallback_count": "0"}
        )

    async def on_coordinates_sent(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_ask_for_help")
        logger.info("sending message...")

        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=_build_options_message(
                translations[self.language.name]["damage_level_question"],
                translations[self.language.name]["damage_level_options"]
            )
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.WAITING_DAMAGE_LEVEL,
            bot_info={"point_id": ctx.point_id, "fallback_count": "0"}
        )

    async def on_damage_level_answered(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_damage_level_answered")

        options = translations[self.language.name]["damage_level_options"]
        raw_answer = ctx.answer

        if raw_answer not in options:
            logger.info(f"Invalid damage level option received: '{raw_answer}', re-asking...")

            await self.message_to_send_store.send_message(
                sender=ctx.sender, to=ctx.recipient,
                message=_build_options_message(translations[self.language.name]["damage_level_question"], options)
            )
            return

        logger.info("storing survey response...")
        point_id = await ctx.fetch_field("point_id")

        if not point_id:
            logger.error(f"Trying to store a survey response for state: '{ctx.state_key}' does not exist point id")
            raise BotStateWithoutPointId(message_id=ctx.message_id)

        await self.survey_responses_store.add_response(
            point_id=point_id,
            question=translations[self.language.name]["damage_level_question"],
            answer=options[raw_answer]
        )

        logger.info("sending message...")
        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=translations[self.language.name]["end_flow"]
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.MAPPING_COMPLETED,
            bot_info={"fallback_count": "0"}
        )

        logger.info("bot flow end, deleting state...")
        await self.bot_state_store.delete_state(
            bot_state_key=ctx.state_key,
        )

    async def on_recovery_choice_answered(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_recovery_choice_answered")

        options = translations[self.language.name]["recovery_options"]
        raw_answer = ctx.answer

        if raw_answer not in options:
            logger.info(f"Invalid recovery option received: '{raw_answer}', re-asking...")

            await self.message_to_send_store.send_message(
                sender=ctx.sender, to=ctx.recipient,
                message=_build_options_message(translations[self.language.name]["recovery_question"], options)
            )
            return

        if raw_answer == "1":
            logger.info("user chose to cancel the flow...")
            await self.message_to_send_store.send_message(
                sender=ctx.sender, to=ctx.recipient,
                message=translations[self.language.name]["flow_cancelled"]
            )
            await self.bot_state_store.delete_state(bot_state_key=ctx.state_key)
            return

        logger.info("user chose to restart the flow...")
        await self.on_ask_for_help(ctx)

    async def on_fallback(self, ctx: BotFlowContext) -> None:
        raw_count = await ctx.fetch_field("fallback_count")
        count = int(raw_count) + 1 if raw_count else 1

        if count > FALLBACK_LIMIT:
            logger.info("fallback limit reached, offering cancel/restart...")

            await self.message_to_send_store.send_message(
                sender=ctx.sender, to=ctx.recipient,
                message=_build_options_message(
                    translations[self.language.name]["recovery_question"],
                    translations[self.language.name]["recovery_options"]
                )
            )
            await self.bot_state_store.save_state(
                bot_state_key=ctx.state_key,
                state=FirstTimeMappingState.WAITING_RECOVERY_CHOICE,
                bot_info={"fallback_count": str(count)}
            )
            return

        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=translations[self.language.name]["fallback"]
        )

        match self.state:
            case FirstTimeMappingState.IDLE | FirstTimeMappingState.WAITING_LANG:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender, to=ctx.recipient,
                    message=_build_options_message(translations[self.language.name]["ask_for_lang_question"],
                                                   _lang_options())
                )
                await self.bot_state_store.save_state(
                    bot_state_key=ctx.state_key,
                    state=FirstTimeMappingState.WAITING_LANG,
                    bot_info={"fallback_count": str(count)}
                )
            case FirstTimeMappingState.WAITING_PHOTO:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender, to=ctx.recipient,
                    message=translations[self.language.name]["ask_for_photo"]
                )
                await self.bot_state_store.save_state(
                    bot_state_key=ctx.state_key,
                    state=FirstTimeMappingState.WAITING_PHOTO,
                    bot_info={"fallback_count": str(count)}
                )
            case FirstTimeMappingState.WAITING_COORDINATES:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender, to=ctx.recipient,
                    message=translations[self.language.name]["ask_for_coordinate"]
                )
                await self.bot_state_store.save_state(
                    bot_state_key=ctx.state_key,
                    state=FirstTimeMappingState.WAITING_COORDINATES,
                    bot_info={"fallback_count": str(count)}
                )
            case FirstTimeMappingState.WAITING_DAMAGE_LEVEL:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender, to=ctx.recipient,
                    message=_build_options_message(
                        translations[self.language.name]["damage_level_question"],
                        translations[self.language.name]["damage_level_options"]
                    )
                )
                await self.bot_state_store.save_state(
                    bot_state_key=ctx.state_key,
                    state=FirstTimeMappingState.WAITING_DAMAGE_LEVEL,
                    bot_info={"fallback_count": str(count)}
                )

    transitions: BotTransitions = {
        (FirstTimeMappingState.IDLE, EventName.USER_SEND_TEXT): on_ask_for_help,
        (FirstTimeMappingState.WAITING_LANG, EventName.USER_SEND_TEXT): on_ask_for_lang,
        (FirstTimeMappingState.WAITING_PHOTO, EventName.USER_UPLOAD_PHOTO): on_photo_uploaded,
        (FirstTimeMappingState.WAITING_COORDINATES, EventName.USER_SEND_COORDINATES): on_coordinates_sent,
        (FirstTimeMappingState.WAITING_DAMAGE_LEVEL, EventName.USER_SEND_TEXT): on_damage_level_answered,
        (FirstTimeMappingState.WAITING_RECOVERY_CHOICE, EventName.USER_SEND_TEXT): on_recovery_choice_answered,
    }
