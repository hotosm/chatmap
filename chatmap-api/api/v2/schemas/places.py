from pydantic import BaseModel, field_validator

MAX_PLACE_NAMES = 20
MAX_PLACE_NAME_LENGTH = 100


class PlaceNames(BaseModel):
    """
    The other names of a place, as the chats write it ("Ein Rihan", "عين
    الريحان"), besides the one it has on the map: a line of a message that
    says one of them names the place. Each once, however it is cased.
    """
    names: list[str] = []

    @field_validator("names")
    @classmethod
    def check_names(cls, names: list[str]) -> list[str]:
        kept: dict[str, str] = {}
        for name in names:
            name = " ".join(name.split())
            if name:
                kept.setdefault(name.casefold(), name)
        if len(kept) > MAX_PLACE_NAMES:
            raise ValueError(f"a place has up to {MAX_PLACE_NAMES} other names")
        if any(len(name) > MAX_PLACE_NAME_LENGTH for name in kept.values()):
            raise ValueError(f"a name takes up to {MAX_PLACE_NAME_LENGTH} characters")
        return list(kept.values())
