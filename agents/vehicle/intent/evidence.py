from typing import Dict, List

from data.knowledge_base import DANGEROUS_KEYWORDS
from rag.documents import INTENT_DOCUMENTS


class IntentEvidenceCollector:
    def __init__(self, retriever):
        self.retriever = retriever

    def collect(self, content: str) -> Dict[str, object]:
        keyword_hits = []
        for document in INTENT_DOCUMENTS:
            for keyword in document.keywords:
                if keyword and keyword.lower() in (content or "").lower():
                    keyword_hits.append(keyword)
        for keyword in DANGEROUS_KEYWORDS:
            if keyword and keyword.lower() in (content or "").lower():
                keyword_hits.append(keyword)
        keyword_hits = _dedupe(keyword_hits)
        retrieval = [
            {
                "doc_id": item.document.doc_id,
                "score": item.score,
                "command_type": item.document.metadata.get("command_type"),
                "matched_keywords": item.matched_keywords,
            }
            for item in self.retriever.search(content, top_k=3)
        ]
        return {"keyword_hits": keyword_hits, "retrieval": retrieval}

    def risk_signals(self, content: str) -> List[str]:
        signals = [
            keyword
            for keyword in DANGEROUS_KEYWORDS
            if keyword and keyword.lower() in (content or "").lower()
        ]
        if contains_actionable_dangerous_control(content):
            signals.append("actionable_dangerous_control")
        return _dedupe(signals)


def contains_actionable_dangerous_control(content: str) -> bool:
    normalized = (content or "").replace(" ", "").lower()
    actionable_patterns = (
        "加速到",
        "立即加速",
        "提升动力",
        "动力提升",
        "立即刹车",
        "执行刹车",
        "紧急制动",
        "执行制动",
        "立即制动",
        "关闭aeb",
        "禁用aeb",
        "关闭自动紧急制动",
        "禁用自动紧急制动",
        "接管方向盘",
        "自动转向",
        "执行转向",
        "帮我转向",
    )
    return any(pattern in normalized for pattern in actionable_patterns)


def contains_any(content: str, keywords) -> bool:
    normalized = (content or "").lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _dedupe(values):
    seen = set()
    return [
        value
        for value in values
        if not (value.lower() in seen or seen.add(value.lower()))
    ]
