from data.knowledge_base import ROUTE_KNOWLEDGE
from data.vehicle_state import DEFAULT_VEHICLE_STATE
from llm.factory import create_llm_client
from providers.destination_resolver import resolve_destination
from providers.factory import create_map_provider
from rag.documents import ROUTE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class CloudRoutePlanAgent:
    def __init__(self, llm_client=None, map_provider=None):
        self.retriever = SimpleRetriever(ROUTE_DOCUMENTS)
        self.llm_client = llm_client or create_llm_client()
        self.map_provider = map_provider or create_map_provider()

    def plan(self, content: str, route_preference: str = "") -> str:
        context = self.retrieve_context(content)
        route_hint = context[0].document.text if context else ""
        if not route_hint:
            route_hint = "长途优先高速路线"
        if route_hint not in ROUTE_KNOWLEDGE:
            route_hint = ROUTE_KNOWLEDGE[0]
        if route_preference:
            route_hint = f"{route_hint}，结合用户路线偏好{route_preference}"
        map_route = self.map_provider.plan_route(
            DEFAULT_VEHICLE_STATE.gps,
            resolve_destination(content),
            preference=route_preference,
        )
        llm_decision = self.llm_client.generate(
            system_prompt=(
                "你是车载云端路线规划 Agent。请基于 RAG、地图路线和用户偏好"
                "生成简洁、可执行、不能越过安全边界的路线建议。"
            ),
            user_prompt=f"用户指令：{content}",
            context={
                "route_hint": route_hint,
                "route_preference": route_preference,
                "map_route": map_route.to_text(),
            },
        )
        return f"RAG路线结果：{content}，{route_hint} | {llm_decision}"

    def retrieve_context(self, content: str):
        return self.retriever.search(content, top_k=2)
