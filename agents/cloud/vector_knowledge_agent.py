from core.constants import CommandType
from agents.cloud.document_rag_agent import DocumentRAGAgent
from agents.cloud.rule_knowledge_agent import RuleKnowledgeAgent
from rag.documents import INTENT_DOCUMENTS, PROFILE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


DOCUMENT_RAG_TRIGGER_MARKERS = (
    "是什么",
    "为什么",
    "怎么",
    "如何",
    "介绍",
    "说明",
    "解释",
    "含义",
    "手册",
    "规则",
    "政策",
    "注意事项",
)


class VectorKnowledgeAgent:
    role_name = "混合知识调度 Agent"

    def __init__(self):
        self.intent_retriever = SimpleRetriever(INTENT_DOCUMENTS)
        self.profile_retriever = SimpleRetriever(PROFILE_DOCUMENTS)
        self.rule_agent = RuleKnowledgeAgent()
        self.document_agent = DocumentRAGAgent()
        self.last_policy = self._empty_policy()

    def retrieve(
        self,
        query: str,
        user_id: str = "",
        command_type: CommandType = None,
        top_k: int = 4,
    ):
        command_type = command_type or CommandType.UNKNOWN
        document_rag_enabled, document_rag_reason = self._should_enable_document_rag(
            query,
            command_type,
        )
        rule_enabled = command_type in {
            CommandType.NAVIGATION,
            CommandType.CHARGE_PLAN,
            CommandType.CAR_CONTROL,
        }
        self.last_policy = {
            "rule_enabled": rule_enabled,
            "document_rag_enabled": document_rag_enabled,
            "document_rag_reason": document_rag_reason,
            "command_type": command_type.value,
        }
        results = []

        if rule_enabled:
            results.extend(
                self.rule_agent.retrieve(query, command_type=command_type, top_k=top_k)
            )

        if document_rag_enabled:
            results.extend(self.document_agent.retrieve(query, top_k=top_k))

        return self._dedupe(results)[: max(1, int(top_k))]

    def summarize(
        self,
        query: str,
        user_id: str = "",
        command_type: CommandType = None,
        top_k: int = 4,
    ) -> str:
        results = self.retrieve(query, user_id=user_id, command_type=command_type, top_k=top_k)
        if not results:
            return "知识库：未召回相关知识"
        rule_fragments = [
            item.document.text
            for item in results
            if item.document.metadata.get("knowledge_type") == "structured_rule"
        ]
        rag_fragments = [
            item.document.text
            for item in results
            if item.document.metadata.get("knowledge_type") == "document_rag"
        ]
        fragments = []
        if rule_fragments:
            fragments.append("规则知识库召回：" + "；".join(rule_fragments))
        if rag_fragments:
            fragments.append("文档RAG召回：" + "；".join(rag_fragments))
        return " | ".join(fragments)

    def retrieve_profile_context(self, user_id: str, query: str = ""):
        profile_query = f"{user_id} {query}".strip()
        return [
            item
            for item in self.profile_retriever.search(profile_query, top_k=2)
            if item.document.metadata.get("user_id") == user_id
        ]

    def retrieve_route_context(self, query: str):
        return self.rule_agent.retrieve(query, command_type=CommandType.NAVIGATION, top_k=2)

    def _should_enable_document_rag(
        self,
        query: str,
        command_type: CommandType,
    ):
        if command_type == CommandType.INFO_QUERY:
            return True, "info_query"
        normalized = query or ""
        if any(marker in normalized for marker in DOCUMENT_RAG_TRIGGER_MARKERS):
            return True, "explanation_request"
        return False, "not_required"

    def _empty_policy(self):
        return {
            "rule_enabled": False,
            "document_rag_enabled": False,
            "document_rag_reason": "not_run",
            "command_type": CommandType.UNKNOWN.value,
        }

    def _dedupe(self, results):
        seen = set()
        unique = []
        for result in results:
            doc_id = result.document.doc_id
            if doc_id in seen:
                continue
            seen.add(doc_id)
            unique.append(result)
        return unique
