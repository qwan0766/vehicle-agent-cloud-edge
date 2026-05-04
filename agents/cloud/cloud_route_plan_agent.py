from data.knowledge_base import ROUTE_KNOWLEDGE
from rag.documents import ROUTE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class CloudRoutePlanAgent:
    def __init__(self):
        self.retriever = SimpleRetriever(ROUTE_DOCUMENTS)

    def plan(self, content: str, route_preference: str = "") -> str:
        context = self.retrieve_context(content)
        route_hint = context[0].document.text if context else ""
        if not route_hint:
            route_hint = "长途优先高速路线"
        if route_hint not in ROUTE_KNOWLEDGE:
            route_hint = ROUTE_KNOWLEDGE[0]
        if route_preference:
            route_hint = f"{route_hint}，结合用户路线偏好{route_preference}"
        return f"RAG路线结果：{content}，{route_hint}"

    def retrieve_context(self, content: str):
        return self.retriever.search(content, top_k=2)
