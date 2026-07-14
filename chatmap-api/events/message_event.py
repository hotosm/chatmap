from dataclasses import dataclass, fields


@dataclass
class MessageEvent:
    id: str
    receiver: str
    sender: str
    chat: str
    text: str
    date: str
    location: str
    photo: str
    video: str
    audio: str
    file: str

    # help to convert a key with a different name
    _aliases = {"from": "sender", "user": "receiver"}

    @classmethod
    def from_dict(cls, data: dict):
        normalized = {cls._aliases.get(k, k): v for k, v in data.items()}
        required_fields = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in normalized.items() if key in required_fields})
