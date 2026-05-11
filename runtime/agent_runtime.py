from time import perf_counter

from core.trace import TraceEvent, normalize_trace_event
from providers.errors import coerce_provider_error


class AgentRuntime:
    def __init__(self, request_id: str = ""):
        self.request_id = request_id
        self._trace = []

    def reset(self, request_id: str = ""):
        if request_id:
            self.request_id = request_id
        self._trace = []

    def call_tool(self, registry, tool_name: str, payload: dict):
        started = perf_counter()
        try:
            output = registry.call(tool_name, payload)
            duration_ms = round((perf_counter() - started) * 1000, 3)
            self.append_trace(
                tool_name=tool_name,
                input=payload,
                output=output,
                duration_ms=duration_ms,
            )
            return output
        except Exception as exc:
            duration_ms = round((perf_counter() - started) * 1000, 3)
            provider_error = coerce_provider_error(
                exc,
                provider=_infer_provider(tool_name, None) or _infer_agent_id(tool_name) or "unknown_provider",
                operation=tool_name,
            )
            self.append_trace(
                tool_name=tool_name,
                input=payload,
                output=provider_error.to_payload(),
                duration_ms=duration_ms,
                status="ERROR",
                provider=provider_error.provider,
                error_code=provider_error.code,
            )
            raise

    def append_trace(
        self,
        tool_name: str = "",
        input: dict = None,
        output=None,
        duration_ms: float = 0.0,
        request_id: str = "",
        agent_id: str = "",
        phase: str = "",
        status: str = "",
        provider: str = "",
        error_code: str = "",
        metadata: dict = None,
        event: TraceEvent = None,
    ):
        inferred_agent_id = agent_id or _infer_agent_id(tool_name)
        inferred_provider = provider or _infer_provider(tool_name, output)
        trace_event = event or {
            "tool_name": tool_name,
            "input": dict(input or {}),
            "output": output,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "agent_id": inferred_agent_id,
            "phase": phase,
            "status": status,
            "provider": inferred_provider,
            "error_code": error_code,
            "metadata": dict(metadata or {}),
        }
        self._trace.append(
            normalize_trace_event(trace_event, request_id=request_id or self.request_id)
        )

    def snapshot(self):
        return [item.to_dict() for item in self._trace]


def _infer_agent_id(tool_name: str) -> str:
    if tool_name.startswith("user_profile."):
        return "UserProfileAgent"
    if tool_name.startswith("knowledge."):
        return "VectorKnowledgeAgent"
    if tool_name.startswith("ecology."):
        return "ExternalEcologyAgent"
    if tool_name.startswith("provider."):
        return "RouteProviderAgent"
    if tool_name.startswith("route."):
        return "RouteProviderAgent"
    if tool_name.startswith("trip."):
        return "GlobalTripPlanningAgent"
    if tool_name.startswith("decision."):
        return "GlobalDispatchAgent"
    if tool_name.startswith("destination."):
        return "DestinationConfidenceAgent"
    return ""


def _infer_provider(tool_name: str, output) -> str:
    if isinstance(output, dict) and output.get("provider"):
        return str(output["provider"])
    if tool_name == "provider.map.route":
        return "map_route"
    if tool_name == "provider.geocode":
        return "geocode"
    if tool_name == "ecology.snapshot":
        return "ecology"
    return ""
