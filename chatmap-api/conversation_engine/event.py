from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from typing import Self

from store.received_messages_store import ReceivedMessage


class EventName(StrEnum):
    USER_SEND_TEXT = auto()
    USER_UPLOAD_PHOTO = auto()
    USER_UPLOAD_VIDEO = auto()
    USER_UPLOAD_AUDIO = auto()
    USER_SEND_COORDINATES = auto()


@dataclass(frozen=True)
class Event:
    name: EventName
    occurred_at: datetime

    @classmethod
    def from_message(cls, message: ReceivedMessage) -> Self | None:
        occurred_at = datetime.fromisoformat(message.date)
        match message:
            case ReceivedMessage(photo=photo) if photo:
                return cls(name=EventName.USER_UPLOAD_PHOTO, occurred_at=occurred_at)
            case ReceivedMessage(video=video) if video:
                return cls(name=EventName.USER_UPLOAD_VIDEO, occurred_at=occurred_at)
            case ReceivedMessage(audio=audio) if audio:
                return cls(name=EventName.USER_UPLOAD_AUDIO, occurred_at=occurred_at)
            case ReceivedMessage(text=text) if text:
                return cls(name=EventName.USER_SEND_TEXT, occurred_at=occurred_at)
            case ReceivedMessage(location=location) if location:
                return cls(name=EventName.USER_SEND_COORDINATES, occurred_at=occurred_at)
            case _:
                return None

    def key(self) -> str:
        return f"{self.occurred_at.timestamp()}:{self.name}"
