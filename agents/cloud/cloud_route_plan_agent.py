from time import perf_counter

from data.vehicle_state import DEFAULT_VEHICLE_STATE
from llm.factory import create_llm_client
from providers.destination_resolver import resolve_destination_detail
from providers.factory import create_geocode_provider, create_map_provider
from rag.documents import ROUTE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class CloudRoutePlanAgent:
    def __init__(self, llm_client=None, map_provider=None, geocoder=None):
        self.retriever = SimpleRetriever(ROUTE_DOCUMENTS)
        self.llm_client = llm_client or create_llm_client()
        self.map_provider = map_provider or create_map_provider()
        self.geocoder = geocoder if geocoder is not None else create_geocode_provider()
        self._provider_trace = []

    def plan(self, content: str, route_preference: str = "", route_context: dict = None) -> str:
        self._provider_trace = []
        route_context = route_context or self.build_route_context(content, route_preference)
        destination = route_context["destination"]
        route_hint = route_context["route_hint"]
        map_route_text = route_context["map_route"]
        route_preference = route_context.get("route_preference", route_preference)
        if "provider_trace" in route_context:
            self._provider_trace = [dict(item) for item in route_context["provider_trace"]]
        else:
            self._provider_trace = []
        llm_decision = self.llm_client.generate(
            system_prompt=(
                "你是车载云端路线规划 Agent。请基于 RAG、地图路线和用户偏好"
                "生成简洁、可执行、不能越过安全边界的路线建议。"
            ),
            user_prompt=f"用户指令：{content}",
            context={
                "destination": destination,
                "route_hint": route_hint,
                "route_preference": route_preference,
                "map_route": map_route_text,
            },
        )
        return (
            f"RAG路线结果：目的地{destination['name']}({destination['gps']})，"
            f"{route_hint} | {llm_decision}"
        )

    def build_route_context(self, content: str, route_preference: str = "") -> dict:
        self._provider_trace = []
        context = self.retrieve_context(content)
        route_hint = context[0].document.text if context else ""
        if not route_hint:
            route_hint = "根据地图路线与用户偏好规划"
        if route_preference:
            route_hint = f"{route_hint}，结合用户路线偏好{route_preference}"
        started = perf_counter()
        destination = resolve_destination_detail(content, geocoder=self.geocoder)
        self._append_provider_trace(
            "provider.geocode",
            {"content": content},
            {
                "destination_name": destination.name,
                "destination_gps": destination.gps,
                "source": destination.source,
            },
            started,
        )
        started = perf_counter()
        map_route = self.map_provider.plan_route(
            DEFAULT_VEHICLE_STATE.gps,
            destination.gps,
            preference=route_preference,
        )
        self._append_provider_trace(
            "provider.map.route",
            {
                "origin": DEFAULT_VEHICLE_STATE.gps,
                "destination": destination.gps,
                "preference": route_preference,
            },
            {
                "provider": map_route.provider,
                "destination_name": destination.name,
                "distance_km": map_route.distance_km,
                "duration_minutes": map_route.duration_minutes,
                "strategy": map_route.strategy,
            },
            started,
        )
        return {
            "destination": {
                "name": destination.name,
                "gps": destination.gps,
                "source": destination.source,
            },
            "route_hint": route_hint,
            "route_preference": route_preference,
            "map_route": map_route.to_text(),
            "route_summary": {
                "provider": map_route.provider,
                "origin": getattr(map_route, "origin", DEFAULT_VEHICLE_STATE.gps),
                "destination": getattr(map_route, "destination", destination.gps),
                "distance_km": map_route.distance_km,
                "duration_minutes": map_route.duration_minutes,
                "strategy": map_route.strategy,
            },
            "provider_trace": self.get_last_provider_trace(),
        }

    def retrieve_context(self, content: str):
        results = self.retriever.search(content, top_k=2)
        high_signal_terms = {"长途", "高速", "跨城", "远途"}
        return [
            item
            for item in results
            if item.document.doc_id != "route_highway_preference"
            or bool(set(item.matched_keywords) & high_signal_terms)
            or any(term in (content or "") for term in high_signal_terms)
        ]

    def get_last_provider_trace(self):
        return [dict(item) for item in self._provider_trace]

    def _append_provider_trace(self, tool_name: str, input_payload: dict, output, started: float):
        self._provider_trace.append(
            {
                "tool_name": tool_name,
                "input": dict(input_payload),
                "output": output,
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "agent_id": "RouteProviderAgent",
                "phase": "provider",
                "status": "OK",
                "provider": _provider_name(tool_name, output),
            }
        )


def _provider_name(tool_name: str, output) -> str:
    if isinstance(output, dict) and output.get("provider"):
        return str(output["provider"])
    if tool_name == "provider.map.route":
        return "map_route"
    if tool_name == "provider.geocode":
        return "geocode"
    return ""
