from rag.corpus_loader import load_markdown_corpus
from rag.documents import DOCUMENT_RAG_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class DocumentRAGAgent:
    role_name = "文档 RAG Agent"

    def __init__(self):
        self.documents = load_markdown_corpus() or DOCUMENT_RAG_DOCUMENTS
        self.retriever = SimpleRetriever(self.documents)

    def retrieve(self, query: str, top_k: int = 3):
        candidates = self.retriever.search(query, top_k=max(top_k * 3, 6))
        filtered = [
            item
            for item in candidates
            if item.matched_keywords or item.score >= 8
        ]
        filtered.sort(
            key=lambda item: (
                len(item.matched_keywords),
                item.score,
                len(item.document.text),
            ),
            reverse=True,
        )
        return filtered[:top_k]

    def summarize(self, query: str, top_k: int = 3) -> str:
        results = self.retrieve(query, top_k=top_k)
        if not results:
            return ""
        return "文档RAG召回：" + "；".join(item.document.text for item in results)
