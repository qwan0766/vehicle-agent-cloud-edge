from core.constants import CommandType
from data.knowledge_base import INTENT_KNOWLEDGE


class LocalIntentAgent:
    def recognize(self, user_input: str) -> CommandType:
        for example, command_type in INTENT_KNOWLEDGE.items():
            if user_input == example or user_input in example:
                return command_type
        return CommandType.UNKNOWN
