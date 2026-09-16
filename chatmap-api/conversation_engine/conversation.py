from conversation_engine.event import Event, EventName
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConversationKey:
    sender: str
    chat: str

    def to_string(self) -> str:
        return f"conversation:{self.sender}:{self.chat}"


@dataclass
class Conversation:
    key: ConversationKey
    log: list[Event] = field(default_factory=list)
    events_viewed: set[EventName] = field(default_factory=set)
