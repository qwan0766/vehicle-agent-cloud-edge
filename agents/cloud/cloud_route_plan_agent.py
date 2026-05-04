from data.knowledge_base import ROUTE_KNOWLEDGE


class CloudRoutePlanAgent:
    def plan(self, content: str) -> str:
        route_hint = "长途优先高速路线"
        if "电量低" in content:
            route_hint = "电量低于20%建议前往换电站"
        elif route_hint not in ROUTE_KNOWLEDGE:
            route_hint = ROUTE_KNOWLEDGE[0]
        return f"RAG路线结果：{content}，{route_hint}"
