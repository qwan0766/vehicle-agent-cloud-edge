import os

from core.constants import CommandType
from data.knowledge_base import DANGEROUS_KEYWORDS, INTENT_KNOWLEDGE
from llm.factory import create_llm_client
from rag.documents import INTENT_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class LocalIntentAgent:
    def __init__(self, llm_client=None, enable_llm_fallback=None):
        self.retriever = SimpleRetriever(INTENT_DOCUMENTS)
        self.llm_client = llm_client or create_llm_client()
        self.enable_llm_fallback = (
            os.getenv("ENABLE_LLM_INTENT_FALLBACK") == "1"
            if enable_llm_fallback is None
            else enable_llm_fallback
        )

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
        if self.enable_llm_fallback:
            return self._recognize_with_llm(user_input)
        return CommandType.UNKNOWN

    def retrieve_context(self, user_input: str):
        return self.retriever.search(user_input, top_k=2)

    def _recognize_with_llm(self, user_input: str) -> CommandType:
        raw = self.llm_client.generate(
            system_prompt=(
                "你是车载意图分类 Agent。只能输出以下枚举之一："
                "NAVIGATION、CAR_CONTROL、CHARGE_PLAN、PERSONALIZE、UNKNOWN。"
            ),
            user_prompt=f"用户指令：{user_input}",
            context={"allowed_intents": [item.value for item in CommandType]},
        ).strip()
        normalized = raw.split()[0].strip().upper()
        for command_type in CommandType:
            if command_type.value == normalized:
                return command_type
        return CommandType.UNKNOWN
