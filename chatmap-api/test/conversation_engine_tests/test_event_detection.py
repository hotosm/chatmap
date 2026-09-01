from conversation_engine.event import Event, EventName
from store.received_messages_store import ReceivedMessage


def _message(**overrides) -> ReceivedMessage:
    fields = {
        "id": "1",
        "receiver": "receiver",
        "sender": "sender",
        "chat": "chat",
        "sender_enc": "sender_enc",
        "chat_enc": "chat_enc",
        "text": "",
        "date": "2026-07-14T12:00:00Z",
        "location": "",
        "photo": "",
        "video": "",
        "audio": "",
        "file": "",
    }
    fields.update(overrides)
    return ReceivedMessage(**fields)


def test_photo_received_state():
    message = _message(photo="photo.jpg")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_UPLOAD_PHOTO


def test_photo_with_a_caption_is_still_a_photo_upload():
    message = _message(photo="photo.jpg", text="hello")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_UPLOAD_PHOTO


def test_video_with_a_caption_is_still_a_video_upload():
    message = _message(video="clip.mp4", text="hello")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_UPLOAD_VIDEO


def test_audio_with_a_caption_is_still_an_audio_upload():
    message = _message(audio="voice.opus", text="hello")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_UPLOAD_AUDIO


def test_coordinates_received_state():
    message = _message(location="-34.6,-58.4")
    event = Event.from_message(message)

    assert event and event.name == EventName.USER_SEND_COORDINATES


def test_unknown_event():
    message = _message()
    event = Event.from_message(message)

    assert event is None
