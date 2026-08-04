from datetime import datetime
from typing import Literal

from store.received_messages_store import ReceivedMessage

MessageType = Literal["photo", "video", "audio", "text", "location"]


def build_message(message_type: MessageType, message_value: str, date: datetime) -> ReceivedMessage:
    stream_id = "stream_id"
    user = "user"
    from_value = "from"
    chat = "chat"
    entry = {
        "id": stream_id,
        "user": user,
        "from": from_value,
        "chat": chat,
        "fromenc": "fromenc",
        "chatenc": "chatenc",
        "text": "",
        "date": date,
        "location": "",
        "photo": "",
        "video": "",
        "audio": "",
        "file": "",
        message_type: message_value
    }

    return ReceivedMessage.from_dict(data=entry)
