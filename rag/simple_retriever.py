from dataclasses import dataclass
from typing import Iterable, List

from rag.documents import RetrievalDocument


@dataclass(frozen=True)
class RetrievalResult:
    document: RetrievalDocument
    score: int
    matched_keywords: List[str]


class SimpleRetriever:
    def __init__(self, documents: Iterable[RetrievalDocument]):
        self.documents = list(documents)

    def search(self, query: str, top_k: int = 3) -> List[RetrievalResult]:
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return []

        results = []
        for document in self.documents:
            result = self._score_document(normalized_query, document)
            if result.score > 0:
                results.append(result)

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    def _score_document(self, normalized_query: str, document: RetrievalDocument) -> RetrievalResult:
        score = 0
        matched_keywords = []
        normalized_text = document.text.lower()

        if normalized_text in normalized_query or normalized_query in normalized_text:
            score += 8

        for keyword in document.keywords:
            normalized_keyword = keyword.lower()
            if normalized_keyword and normalized_keyword in normalized_query:
                score += 3
                matched_keywords.append(keyword)

        if not matched_keywords and len(normalized_query) >= 4:
            overlap = set(normalized_query) & set(normalized_text)
            if len(overlap) >= 3:
                score += len(overlap)

        return RetrievalResult(
            document=document,
            score=score,
            matched_keywords=matched_keywords,
        )
