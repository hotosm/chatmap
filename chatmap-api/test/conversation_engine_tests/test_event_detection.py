import pytest

from events.message_event import MessageEvent
from conversation_engine.event import Event, EventName


def _message(**overrides) -> MessageEvent:
    fields = {
        "id": "1",
        "receiver": "receiver",
        "sender": "sender",
        "chat": "chat",
        "text": "",
        "date": "2026-07-14T12:00:00Z",
        "location": "",
        "photo": "",
        "video": "",
        "audio": "",
        "file": "",
    }
    fields.update(overrides)
    return MessageEvent(**fields)


def test_photo_received_state():
    message = _message(photo="photo.jpg")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_UPLOAD_PHOTO


def test_photo_with_text_received_state():
    message = _message(photo="photo.jpg", text="hello")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_UPLOAD_PHOTO_WITH_TEXT


def test_coordinates_received_state():
    message = _message(location="-34.6,-58.4")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_SEND_COORDINATES


def test_unknown_event():
    message = _message()
    event = Event.from_message(message)

    assert event is None
