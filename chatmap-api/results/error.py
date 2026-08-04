class StoreUnavailable(Exception):
    ...


class UnknownConversation(Exception):
    ...


class BotStateWithoutPointId(Exception):
    def __init__(self, message_id):
        self.message_id = message_id
