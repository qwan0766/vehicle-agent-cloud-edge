from core.constants import CommandType
from rag.documents import INTENT_DOCUMENTS, PROFILE_DOCUMENTS, ROUTE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class VectorKnowledgeAgent:
    role_name = "向量知识库 Agent"

    def __init__(self):
        self.intent_retriever = SimpleRetriever(INTENT_DOCUMENTS)
        self.profile_retriever = SimpleRetriever(PROFILE_DOCUMENTS)
        self.route_retriever = SimpleRetriever(ROUTE_DOCUMENTS)

    def retrieve(
        self,
        query: str,
        user_id: str = "",
        command_type: CommandType = None,
        top_k: int = 4,
    ):
        command_type = command_type or CommandType.UNKNOWN
        results = []

        results.extend(self.intent_retriever.search(query, top_k=1))

        if user_id:
            profile_query = f"{user_id} {query}".strip()
            results.extend(
                item
                for item in self.profile_retriever.search(profile_query, top_k=2)
                if item.document.metadata.get("user_id") == user_id
            )

        if command_type in {CommandType.NAVIGATION, CommandType.CHARGE_PLAN}:
            results.extend(self.route_retriever.search(query, top_k=2))

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
            return "向量知识库：未召回相关知识"
        fragments = [item.document.text for item in results]
        return "向量知识库召回：" + "；".join(fragments)

    def retrieve_profile_context(self, user_id: str, query: str = ""):
        profile_query = f"{user_id} {query}".strip()
        return [
            item
            for item in self.profile_retriever.search(profile_query, top_k=2)
            if item.document.metadata.get("user_id") == user_id
        ]

    def retrieve_route_context(self, query: str):
        return self.route_retriever.search(query, top_k=2)

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
