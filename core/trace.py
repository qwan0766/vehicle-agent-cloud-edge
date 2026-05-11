from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


TRACE_STATUS_OK = "OK"
TRACE_STATUS_ERROR = "ERROR"


@dataclass(frozen=True)
class TraceEvent:
    """Standard runtime trace event shared by agents, providers, and UI."""

    tool_name: str
    input: Dict[str, Any] = field(default_factory=dict)
    output: Any = ""
    duration_ms: float = 0.0
    request_id: str = ""
    agent_id: str = ""
    phase: str = "tool"
    status: str = TRACE_STATUS_OK
    provider: str = ""
    error_code: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "input": dict(self.input),
            "output": self.output,
            "duration_ms": self.duration_ms,
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "phase": self.phase,
            "status": self.status,
            "provider": self.provider,
            "error_code": self.error_code,
            "metadata": dict(self.metadata),
        }


def normalize_trace_event(
    event: Any,
    request_id: str = "",
    agent_id: str = "",
    phase: str = "",
    status: str = "",
    provider: str = "",
    error_code: str = "",
    metadata: Optional[Mapping[str, Any]] = None,
) -> TraceEvent:
    if isinstance(event, TraceEvent):
        payload = event.to_dict()
    elif isinstance(event, Mapping):
        payload = dict(event)
    else:
        raise TypeError("trace event must be TraceEvent or mapping")

    merged_metadata = dict(payload.get("metadata") or {})
    merged_metadata.update(dict(metadata or {}))

    return TraceEvent(
        tool_name=str(payload.get("tool_name") or ""),
        input=dict(payload.get("input") or {}),
        output=payload.get("output", ""),
        duration_ms=_safe_float(payload.get("duration_ms"), 0.0),
        request_id=str(payload.get("request_id") or request_id or ""),
        agent_id=str(payload.get("agent_id") or agent_id or ""),
        phase=str(payload.get("phase") or phase or "tool"),
        status=str(payload.get("status") or status or TRACE_STATUS_OK),
        provider=str(payload.get("provider") or provider or ""),
        error_code=str(payload.get("error_code") or error_code or ""),
        metadata=merged_metadata,
    )


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
