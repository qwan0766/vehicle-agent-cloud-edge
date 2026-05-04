from core.constants import CommandType
from data.knowledge_base import DANGEROUS_KEYWORDS, INTENT_KNOWLEDGE


class LocalIntentAgent:
    def recognize(self, user_input: str) -> CommandType:
        for example, command_type in INTENT_KNOWLEDGE.items():
            if user_input == example or user_input in example:
                return command_type
        for keyword in DANGEROUS_KEYWORDS:
            if keyword in user_input:
                return CommandType.CAR_CONTROL
        return CommandType.UNKNOWN
