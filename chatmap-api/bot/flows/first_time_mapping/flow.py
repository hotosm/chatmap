from bot.flow import BotFlow, BotTransitions, BotFlowContext, not_handler_created, Language
from conversation_engine.event import EventName
from enum import Enum, auto
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore

from pathlib import Path
import json

import logging

logger = logging.getLogger(__name__)

_MESSAGES_PATH = Path(__file__).parent / "messages.json"

with open(_MESSAGES_PATH, encoding="utf-8") as f:
    translations = json.load(f)


class FirstTimeMappingState(Enum):
    IDLE = auto()
    WAITING_LANG = auto()
    WAITING_PHOTO = auto()
    WAITING_COORDINATES = auto()
    MAPPING_COMPLETED = auto()


class FirstTimeMappingFlow(BotFlow):
    name = "first_time_mapping_flow"

    @classmethod
    async def create(
            cls,
            bot_state_key: str,
            bot_state_store: BotStateStore,
            message_to_send_store: MessageToSendStore
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

        return cls(state=state, language=language, bot_state_store=bot_state_store,
                   message_to_send_store=message_to_send_store)

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
            message=translations[self.language.name]["ask_for_lang"]
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.WAITING_LANG
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
                message=translations[self.language.name]["ask_for_lang"]
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
            bot_info={"lang": language_key}
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
            state=FirstTimeMappingState.WAITING_COORDINATES
        )

    async def on_coordinates_sent(self, ctx: BotFlowContext) -> None:
        logger.info("Handling: on_ask_for_help")
        logger.info("sending message...")

        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=translations[self.language.name]["end_flow"]
        )

        logger.info("storing new bot event...")
        await self.bot_state_store.save_state(
            bot_state_key=ctx.state_key,
            state=FirstTimeMappingState.MAPPING_COMPLETED
        )

        logger.info("bot flow end, deleting state...")
        await self.bot_state_store.delete_state(
            bot_state_key=ctx.state_key,
        )

    async def on_fallback(self, ctx: BotFlowContext) -> None:
        await self.message_to_send_store.send_message(
            sender=ctx.sender, to=ctx.recipient,
            message=translations[self.language.name]["fallback"]
        )

        match self.state:
            case FirstTimeMappingState.IDLE:
                await self.on_ask_for_help(ctx)
            case FirstTimeMappingState.WAITING_LANG:
                await self.on_ask_for_help(ctx)
            case FirstTimeMappingState.WAITING_PHOTO:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender, to=ctx.recipient,
                    message=translations[self.language.name]["ask_for_photo"]
                )
            case FirstTimeMappingState.WAITING_COORDINATES:
                await self.message_to_send_store.send_message(
                    sender=ctx.sender, to=ctx.recipient,
                    message=translations[self.language.name]["ask_for_coordinate"]
                )

    transitions: BotTransitions = {
        (FirstTimeMappingState.IDLE, EventName.USER_SEND_TEXT): on_ask_for_help,
        (FirstTimeMappingState.WAITING_LANG, EventName.USER_SEND_TEXT): on_ask_for_lang,
        (FirstTimeMappingState.WAITING_PHOTO, EventName.USER_UPLOAD_PHOTO): on_photo_uploaded,
        (FirstTimeMappingState.WAITING_COORDINATES, EventName.USER_SEND_COORDINATES): on_coordinates_sent,
    }
