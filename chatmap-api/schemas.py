from typing import List, Literal, Tuple
from datetime import datetime

from pydantic import BaseModel, model_validator

from bot.configured_messages import BotStep


class FeatureGeometry(BaseModel):
    """
    Represents the geometry of a GeoJSON feature (Point).
    """
    type: Literal["Point"]
    coordinates: Tuple[float, float]  # GeoJSON is [lon, lat]


class FeatureProperties(BaseModel):
    """
    Represents the properties of a GeoJSON feature.
    """
    id: str
    time: datetime
    # username_id: str
    message: str | None = None
    file: str | None
    file_embedded: str | None
    removed: bool = False
    tags: str = ""


class Feature(BaseModel):
    """
    Represents a GeoJSON feature.
    """
    type: Literal["Feature"]
    geometry: FeatureGeometry
    properties: FeatureProperties


class FeatureCollection(BaseModel):
    """
    Represents a GeoJSON FeatureCollection.
    """
    id: str
    sharing: str
    owner: bool
    is_live: bool
    name: str
    description: str | None = None
    type: Literal["FeatureCollection"]
    centroid: str = ""
    features: List[Feature] = []


class SaveMapFeatureProperties(BaseModel):
    """
    Represents the properties of a GeoJSON feature.
    """
    time: datetime
    message: str | None = None
    file: str | None = None
    file_type: str | None = None
    username: str
    tags: str = ""
    removed: bool = False


class SaveMapFeature(BaseModel):
    type: Literal["Feature"]
    geometry: FeatureGeometry
    properties: SaveMapFeatureProperties


class SaveMapFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    name: str
    description: str | None = None
    features: List[SaveMapFeature]


class UpdateMap(BaseModel):
    name: str
    description: str | None = None


# Options are rendered with keycap emoji, which run out at the tenth
MIN_OPTIONS = 2
MAX_OPTIONS = 10

# Steps the bot may send but that expect no answer, so they carry no error message
REQUIRED_TEXT_STEPS = (BotStep.START, BotStep.END)
# Steps the bot asks something with, so they need their "incorrect answer" too
REQUIRED_ANSWERING_STEPS = (BotStep.MEDIA, BotStep.LOCATION)


def _filled(text: str | None) -> bool:
    return bool((text or "").strip())


class BotConfiguredMessage(BaseModel):
    """
    One configurable message of a map's bot conversation. A message without
    an id is a new one; the id of an existing message is preserved across
    edits because the survey cursor matches answers on it.
    """
    id: str | None = None
    bot_step: BotStep
    position: int | None = None
    prompt: str = ""
    error_message: str | None = None
    options: List[str] = []


class BotMaxAttemptsMessages(BaseModel):
    """
    The message sent once the user has failed too many times in a row, and
    the two answers offered to cancel or restart. Configured through its own
    field, not as a message among `messages`, since the bot needs to know
    which answer does what rather than a free list of options.
    """
    id: str | None = None
    max_attempts_quantity: int = 3
    notify_message: str = ""
    to_restart: str = ""
    to_cancel: str = ""


class BotSetupResult(BaseModel):
    """
    A map's whole bot configuration as it is stored. Reports what is there,
    without judging it - the rules below govern what may be written, not what
    may be read back.
    """
    bot_active: bool = False
    messages: List[BotConfiguredMessage] = []
    max_attempts_messages: BotMaxAttemptsMessages = BotMaxAttemptsMessages()


class BotSetup(BotSetupResult):
    """
    An incoming bot configuration. The bot cannot be enabled while a message
    it needs is missing, and a half-written question is rejected either way.
    """

    @model_validator(mode="after")
    def check_messages(self):
        singles = [message for message in self.messages if message.bot_step == BotStep.SINGLE_CHOICE]
        fixed = {}

        for message in self.messages:
            if message.bot_step == BotStep.SINGLE_CHOICE:
                continue
            if message.bot_step == BotStep.MAX_ATTEMPTS:
                raise ValueError(
                    "the max attempts message is configured through 'max_attempts_messages', not 'messages'"
                )
            if message.bot_step in fixed:
                raise ValueError(f"'{message.bot_step.value}' can only be configured once")
            fixed[message.bot_step] = message

        # A half-written question is not something the bot can ask, so this
        # holds whether or not the bot is enabled
        for question in singles:
            if not _filled(question.prompt):
                raise ValueError("every single choice question needs its question text")
            if not _filled(question.error_message):
                raise ValueError("every single choice question needs an incorrect answer message")
            if not MIN_OPTIONS <= len([o for o in question.options if _filled(o)]) <= MAX_OPTIONS:
                raise ValueError(
                    f"a single choice question needs between {MIN_OPTIONS} and {MAX_OPTIONS} options"
                )

        if not self.bot_active:
            return self

        for step in REQUIRED_TEXT_STEPS + REQUIRED_ANSWERING_STEPS:
            message = fixed.get(step)
            if message is None or not _filled(message.prompt):
                raise ValueError(f"the bot cannot be enabled without a '{step.value}' message")

        for step in REQUIRED_ANSWERING_STEPS:
            if not _filled(fixed[step].error_message):
                raise ValueError(f"the bot cannot be enabled without an incorrect answer for '{step.value}'")

        attempts = self.max_attempts_messages
        if not _filled(attempts.notify_message) or not _filled(attempts.to_restart) or not _filled(attempts.to_cancel):
            raise ValueError("the bot cannot be enabled without the max attempts message and its two options")
        if attempts.max_attempts_quantity < 1:
            raise ValueError("the max attempts quantity must be at least 1")

        return self


class AddPointsFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[SaveMapFeature]


class SaveMapResult(BaseModel):
    id: str
    name: str


class AddPointsResult(BaseModel):
    id: str
    count: int


class SaveMediaResponse(BaseModel):
    uri: str


class PointTags(BaseModel):
    tags: str = ""
