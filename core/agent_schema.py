from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional

from core.constants import (
    CommandType,
    ExecutionStatus,
    NetworkStatus,
    SafetyLevel,
)
from core.trace import TraceEvent, normalize_trace_event


@dataclass(frozen=True)
class IntentFrame:
    request_id: str
    user_id: str
    raw_input: str
    normalized_input: str
    command_type: CommandType
    safety: SafetyLevel
    network: NetworkStatus
    content: str = ""
    confidence: float = 1.0
    source: str = "message"
    slots: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_message(
        cls,
        message,
        raw_input: Optional[str] = None,
        normalized_input: Optional[str] = None,
        confidence: float = 1.0,
        source: str = "message",
        slots: Optional[Mapping[str, Any]] = None,
    ) -> "IntentFrame":
        content = str(getattr(message, "content", ""))
        return cls(
            request_id=str(getattr(message, "request_id", "")),
            user_id=str(getattr(message, "user_id", "")),
            raw_input=str(raw_input if raw_input is not None else content),
            normalized_input=str(
                normalized_input if normalized_input is not None else content
            ),
            command_type=getattr(message, "command_type"),
            safety=getattr(message, "safety"),
            network=getattr(message, "network"),
            content=content,
            confidence=_safe_float(confidence, 1.0),
            source=source,
            slots=dict(slots or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "raw_input": self.raw_input,
            "normalized_input": self.normalized_input,
            "content": self.content,
            "command_type": _enum_value(self.command_type),
            "safety": _enum_value(self.safety),
            "network": _enum_value(self.network),
            "confidence": self.confidence,
            "source": self.source,
            "slots": dict(self.slots),
        }


@dataclass(frozen=True)
class VehicleStateFrame:
    speed_kmh: int
    battery_percent: int
    network: NetworkStatus
    gps: str
    road_type: str = ""
    speed_limit_kmh: int = 0
    driver_assist_mode: str = ""
    vehicle_ready: bool = True
    lane_confidence: float = 0.0

    @classmethod
    def from_vehicle_state(cls, vehicle_state) -> "VehicleStateFrame":
        return cls(
            speed_kmh=int(getattr(vehicle_state, "speed_kmh", 0)),
            battery_percent=int(getattr(vehicle_state, "battery_percent", 0)),
            network=getattr(vehicle_state, "network", NetworkStatus.ONLINE),
            gps=str(getattr(vehicle_state, "gps", "")),
            road_type=_enum_value(getattr(vehicle_state, "road_type", "")),
            speed_limit_kmh=int(getattr(vehicle_state, "speed_limit_kmh", 0)),
            driver_assist_mode=_enum_value(
                getattr(vehicle_state, "driver_assist_mode", "")
            ),
            vehicle_ready=bool(getattr(vehicle_state, "vehicle_ready", True)),
            lane_confidence=_safe_float(
                getattr(vehicle_state, "lane_confidence", 0.0),
                0.0,
            ),
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "VehicleStateFrame":
        return cls(
            speed_kmh=_safe_int(payload.get("speed_kmh"), 0),
            battery_percent=_safe_int(payload.get("battery_percent"), 0),
            network=_network_value(payload.get("network")),
            gps=str(payload.get("gps") or ""),
            road_type=str(_enum_value(payload.get("road_type") or "")),
            speed_limit_kmh=_safe_int(payload.get("speed_limit_kmh"), 0),
            driver_assist_mode=str(
                _enum_value(payload.get("driver_assist_mode") or "")
            ),
            vehicle_ready=bool(payload.get("vehicle_ready", True)),
            lane_confidence=_safe_float(payload.get("lane_confidence"), 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speed_kmh": self.speed_kmh,
            "battery_percent": self.battery_percent,
            "network": _enum_value(self.network),
            "gps": self.gps,
            "road_type": self.road_type,
            "speed_limit_kmh": self.speed_limit_kmh,
            "driver_assist_mode": self.driver_assist_mode,
            "vehicle_ready": self.vehicle_ready,
            "lane_confidence": self.lane_confidence,
        }


@dataclass(frozen=True)
class ProviderResultFrame:
    request_id: str = ""
    agent_id: str = ""
    provider: str = ""
    capability: str = ""
    status: str = "OK"
    payload: Any = ""
    latency_ms: float = 0.0
    error_code: str = ""
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_trace_event(cls, event: Any) -> "ProviderResultFrame":
        trace = normalize_trace_event(event)
        metadata = dict(trace.metadata or {})
        return cls(
            request_id=trace.request_id,
            agent_id=trace.agent_id,
            provider=trace.provider or trace.tool_name,
            capability=str(metadata.get("capability") or trace.phase or "tool"),
            status=trace.status,
            payload=trace.output,
            latency_ms=trace.duration_ms,
            error_code=trace.error_code,
            error_message=str(metadata.get("error_message") or ""),
            metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "provider": self.provider,
            "capability": self.capability,
            "status": self.status,
            "payload": self.payload,
            "latency_ms": self.latency_ms,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class AgentTraceFrame:
    request_id: str
    agent_id: str
    scope: str
    description: str = ""
    status: str = "OK"
    outputs: List[ProviderResultFrame] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_id": self.agent_id,
            "scope": self.scope,
            "description": self.description,
            "status": self.status,
            "outputs": [output.to_dict() for output in self.outputs],
        }


@dataclass(frozen=True)
class ExecutionResultFrame:
    request_id: str
    status: ExecutionStatus
    output: str
    intent: IntentFrame
    feedback: Dict[str, Any] = field(default_factory=dict)
    trace: List[ProviderResultFrame] = field(default_factory=list)
    local_context: Dict[str, Any] = field(default_factory=dict)
    graph: Dict[str, Any] = field(default_factory=dict)
    clarification: Dict[str, Any] = field(default_factory=dict)
    pending_action: Dict[str, Any] = field(default_factory=dict)
    input_rewrite: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_result(cls, result) -> "ExecutionResultFrame":
        message = getattr(result, "message")
        return cls(
            request_id=str(getattr(message, "request_id", "")),
            status=getattr(result, "status"),
            output=str(getattr(result, "output", "")),
            intent=IntentFrame.from_message(message),
            feedback=dict(getattr(result, "feedback", None) or {}),
            trace=_provider_frames(getattr(result, "trace", None) or []),
            local_context=dict(getattr(result, "local_context", None) or {}),
            graph=dict(getattr(result, "graph", None) or {}),
            clarification=dict(getattr(result, "clarification", None) or {}),
            pending_action=dict(getattr(result, "pending_action", None) or {}),
            input_rewrite=dict(getattr(result, "input_rewrite", None) or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": _enum_value(self.status),
            "output": self.output,
            "intent": self.intent.to_dict(),
            "feedback": dict(self.feedback),
            "trace": [item.to_dict() for item in self.trace],
            "local_context": dict(self.local_context),
            "graph": dict(self.graph),
            "clarification": dict(self.clarification),
            "pending_action": dict(self.pending_action),
            "input_rewrite": dict(self.input_rewrite),
        }


def _provider_frames(events: Iterable[Any]) -> List[ProviderResultFrame]:
    frames = []
    for event in events:
        if isinstance(event, ProviderResultFrame):
            frames.append(event)
        elif isinstance(event, (TraceEvent, Mapping)):
            frames.append(ProviderResultFrame.from_trace_event(event))
    return frames


def _enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _network_value(value: Any) -> NetworkStatus:
    if isinstance(value, NetworkStatus):
        return value
    try:
        return NetworkStatus(str(value))
    except ValueError:
        return NetworkStatus.ONLINE


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
