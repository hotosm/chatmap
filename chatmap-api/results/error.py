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
