class StoreUnavailable(Exception):
    ...


class UnknownConversation(Exception):
    ...


class BotStateWithoutPointId(Exception):
    def __init__(self, message_id):
        self.message_id = message_id


class BotStateWithoutQuestion(Exception):
    def __init__(self, message_id):
        self.message_id = message_id


class BotMessagesNotConfigured(Exception):
    def __init__(self, message_id):
        self.message_id = message_id


class NotAuthorized(Exception):
    ...


class UnsupportedMediaType(Exception):
    def __init__(self, extension):
        self.extension = extension


class PointAlreadyHasMedia(Exception):
    def __init__(self, point_id):
        self.point_id = point_id


class UnknownStatus(Exception):
    def __init__(self, status_id):
        self.status_id = status_id


class ArchivedStatus(Exception):
    def __init__(self, status_id):
        self.status_id = status_id


class StatusInUse(Exception):
    def __init__(self, status_ids):
        self.status_ids = status_ids


class MapNotFound(Exception):
    ...


class PointIdAlreadyTaken(Exception):
    def __init__(self, point_id):
        self.point_id = point_id


class UnknownTagChange(Exception):
    def __init__(self, change_id):
        self.change_id = change_id


class UnknownKey(Exception):
    def __init__(self, key_id):
        self.key_id = key_id


class BuiltinKey(Exception):
    def __init__(self, key_id):
        self.key_id = key_id


class KeyNameTaken(Exception):
    def __init__(self, name):
        self.name = name


class KeyInUse(Exception):
    def __init__(self, key_id):
        self.key_id = key_id


class UnknownValue(Exception):
    def __init__(self, value_id):
        self.value_id = value_id


class ArchivedValue(Exception):
    def __init__(self, value_id):
        self.value_id = value_id


class ValueInUse(Exception):
    def __init__(self, value_ids):
        self.value_ids = value_ids


class InvalidTagValue(Exception):
    def __init__(self, reason):
        self.reason = reason
