from core.constants import CommandType
from data.knowledge_base import DANGEROUS_KEYWORDS, INTENT_KNOWLEDGE
from rag.documents import INTENT_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class LocalIntentAgent:
    def __init__(self):
        self.retriever = SimpleRetriever(INTENT_DOCUMENTS)

    def recognize(self, user_input: str) -> CommandType:
        for example, command_type in INTENT_KNOWLEDGE.items():
            if user_input == example or user_input in example:
                return command_type
        results = self.retriever.search(user_input, top_k=1)
        if results:
            return results[0].document.metadata["command_type"]
        for keyword in DANGEROUS_KEYWORDS:
            if keyword in user_input:
                return CommandType.CAR_CONTROL
        return CommandType.UNKNOWN

    def retrieve_context(self, user_input: str):
        return self.retriever.search(user_input, top_k=2)
