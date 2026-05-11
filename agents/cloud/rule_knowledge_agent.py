from core.constants import CommandType
from rag.documents import ROUTE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class RuleKnowledgeAgent:
    role_name = "规则知识库 Agent"

    def __init__(self):
        self.retriever = SimpleRetriever(ROUTE_DOCUMENTS)

    def retrieve(self, query: str, command_type: CommandType = None, top_k: int = 4):
        command_type = command_type or CommandType.UNKNOWN
        results = [
            item
            for item in self.retriever.search(query, top_k=top_k)
            if item.document.metadata.get("knowledge_type") == "structured_rule"
            and self._is_relevant(item, query, command_type)
        ]
        return results[: max(1, int(top_k))]

    def summarize(self, query: str, command_type: CommandType = None, top_k: int = 4) -> str:
        results = self.retrieve(query, command_type=command_type, top_k=top_k)
        if not results:
            return ""
        return "规则知识库召回：" + "；".join(item.document.text for item in results)

    def _is_relevant(self, result, query: str, command_type: CommandType) -> bool:
        doc_id = result.document.doc_id
        text = query or ""
        matched = set(result.matched_keywords)

        if doc_id == "route_highway_preference":
            high_signal_terms = {"长途", "高速", "跨城", "远途"}
            return bool(matched & high_signal_terms) or any(
                term in text for term in high_signal_terms
            )

        if doc_id == "route_offline_navigation":
            return any(term in text for term in {"断网", "离线", "网络"})

        if doc_id in {"route_low_battery_swap", "route_swap_duration"}:
            return command_type == CommandType.CHARGE_PLAN or any(
                term in text for term in {"电量低", "补能", "充电", "换电"}
            )

        if doc_id == "route_comfort_temperature":
            return command_type == CommandType.CAR_CONTROL or any(
                term in text for term in {"温度", "空调", "舒适"}
            )

        return result.score >= 6
