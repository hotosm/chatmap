from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from events.message_event import MessageEvent
from typing import Self


class EventName(StrEnum):
    USER_UPLOAD_PHOTO = auto()
    USER_UPLOAD_PHOTO_WITH_TEXT = auto()
    USER_SEND_COORDINATES = auto()


@dataclass(frozen=True)
class Event:
    name: EventName
    occurred_at: datetime

    @classmethod
    def from_message(cls, message: MessageEvent) -> Self | None:
        occurred_at = datetime.fromisoformat(message.date)
        match message:
            case MessageEvent(photo=photo, text=text) if photo and text:
                # TODO: we should use the message.date field?
                return cls(name=EventName.USER_UPLOAD_PHOTO_WITH_TEXT, occurred_at=occurred_at)
            case MessageEvent(photo=photo) if photo:
                # TODO: we should use the message.date field?
                return cls(name=EventName.USER_UPLOAD_PHOTO, occurred_at=occurred_at)
            case MessageEvent(location=location) if location:
                # TODO: we should use the message.date field?
                return cls(name=EventName.USER_SEND_COORDINATES, occurred_at=occurred_at)
            case _:
                return None

    def key(self) -> str:
        return f"{self.occurred_at.timestamp()}:{self.name}"
