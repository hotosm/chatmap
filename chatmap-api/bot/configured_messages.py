from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

# Options are numbered for the user; the schema caps them at ten for this reason
_OPTION_NUMBER = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


@dataclass
class BotMaxAttemptsMessages:
    max_attempts_quantity: int
    notify_message: str
    to_restart: str
    to_cancel: str

    def full_message(self) -> str:
        """The warning plus its two answers, as one sentence ready to send."""
        return f"{self.notify_message} {self.to_cancel}, {self.to_restart}"


class BotStep(str, Enum):
    START = "start"
    MEDIA = "media"
    LOCATION = "location"
    SINGLE_CHOICE = "single_choice"
    MAX_ATTEMPTS = "max_attempts"
    END = "end"

    def __repr__(self) -> str:
        return f"<{self.value!r}>"


@dataclass
class BotMessage:
    id: str
    bot_step: BotStep
    prompt: str
    error_message: str
    options: list[str] = field(default_factory=list)


@dataclass
class BotConfiguredMessages:
    max_attempts_messages: BotMaxAttemptsMessages
    messages: list[BotMessage] = field(default_factory=list)

    def message_for(self, step: BotStep) -> BotMessage | None:
        return next((message for message in self.messages if message.bot_step == step), None)

    def survey_questions(self) -> list[BotMessage]:
        """The owner's own single choice questions, in their configured order."""
        return [message for message in self.messages if message.bot_step == BotStep.SINGLE_CHOICE]

    def has_survey_questions(self) -> bool:
        return len(self.survey_questions()) > 0

    def next_question_to_answer(self, answered_ids: set[str]) -> BotMessage | None:
        """The first configured question still missing an answer, or None when the survey is done."""
        return next((question for question in self.survey_questions() if question.id not in answered_ids), None)

    def text_of(self, step: BotStep) -> str:
        message = self.message_for(step)
        return message.prompt if message else ""

    def error_of(self, step: BotStep) -> str:
        message = self.message_for(step)
        return (message.error_message or "") if message else ""

    @classmethod
    def build_options_message(cls, question: str, options: list[str]) -> str:
        options_text = "\n".join(
            f"{_OPTION_NUMBER[index] if index < len(_OPTION_NUMBER) else f'{index + 1}.'} {label}"
            for index, label in enumerate(options)
        )
        return f"{question}\n\n{options_text}"

    @classmethod
    def selected_option(cls, answer: str, options: list[str]) -> str | None:
        choice = (answer or "").strip()

        if not choice.isdigit():
            return None

        index = int(choice)
        return options[index - 1] if 1 <= index <= len(options) else None
