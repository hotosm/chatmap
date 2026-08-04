import base64
import logging

from Crypto.Cipher import AES

from bot.flow import BotFlowContext
from conversation_engine.conversation import Conversation
from conversation_engine.event import Event, EventName
from bot.flows.first_time_mapping.flow import FirstTimeMappingFlow
from store.bot_consumed_messages_store import BotConsumedMessagesStore
from store.bot_state_store import BotStateStore
from store.message_to_send_store import MessageToSendStore
from store.survey_responses_store import SurveyResponsesStore
from settings import CHATMAP_ENC_KEY
from store.received_messages_store import ReceivedMessage

logger = logging.getLogger(__name__)


# TODO: duplicated from data.py's decrypt_message; extract to a shared module.
def _decrypt_text(encoded_data: str) -> str:
    if not encoded_data:
        return encoded_data

    key = CHATMAP_ENC_KEY.encode("utf-8")
    raw = base64.b64decode(encoded_data)
    nonce_size = 12
    nonce = raw[:nonce_size]
    ciphertext = raw[nonce_size:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext[:-16], ciphertext[-16:])
    return plaintext.decode("utf-8")


class BotTool:
    def __init__(
            self, bot_state_store: BotStateStore,
            message_to_send_store: MessageToSendStore,
            bot_consumed_messages_store: BotConsumedMessagesStore,
            survey_responses_store: SurveyResponsesStore
    ):
        self.bot_state_store = bot_state_store
        self.message_to_send_store = message_to_send_store
        self.bot_consumed_messages_store = bot_consumed_messages_store
        self.survey_responses_store = survey_responses_store

    async def __call__(self, event: Event, message: ReceivedMessage, device: str, conversation: Conversation):
        bot_state_key = f"bot_state:{FirstTimeMappingFlow.name}:{message.sender}{message.chat}"

        flow = await FirstTimeMappingFlow.create(
            bot_state_key=bot_state_key,
            bot_state_store=self.bot_state_store,
            message_to_send_store=self.message_to_send_store,
            bot_consumed_messages_store=self.bot_consumed_messages_store,
            survey_responses_store=self.survey_responses_store
        )

        point_id = message.id if event.name == EventName.USER_SEND_COORDINATES else None

        context = BotFlowContext(
            state_key=bot_state_key,
            recipient=message.sender_enc,
            sender=device,
            answer=_decrypt_text(message.text),
            message_id=message.id,
            occurred_at=event.occurred_at,
            point_id=point_id,
            bot_state_store=self.bot_state_store
        )

        await flow.call(current_event=event.name, context=context)
