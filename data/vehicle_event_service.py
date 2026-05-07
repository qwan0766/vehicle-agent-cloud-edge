from datetime import datetime, timezone

from agents.vehicle.vehicle_state_monitor_agent import VehicleStateMonitorAgent
from core.constants import NetworkStatus


class VehicleEventService:
    def __init__(self, monitor_agent=None):
        self.monitor_agent = monitor_agent or VehicleStateMonitorAgent()

    def snapshot(self, vehicle_state, network: NetworkStatus = None) -> dict:
        raw_events = self.monitor_agent.detect_events(vehicle_state)
        return {
            "vehicle_state": _vehicle_state_payload(vehicle_state, network),
            "events": [self._normalize_event(event) for event in raw_events],
            "event_rules": event_rules(),
        }

    def _normalize_event(self, event: dict) -> dict:
        event_type = event.get("type", "STATE_EVENT")
        severity = _severity_for(event_type)
        return {
            "event_id": _event_id(event_type),
            "type": event_type,
            "severity": severity,
            "status": "ACTIVE",
            "source_agent": self.monitor_agent.__class__.__name__,
            "command_type": event.get("command_type", ""),
            "content": event.get("content", ""),
            "trigger": event.get("trigger", "AUTO"),
            "reason": event.get("reason", ""),
            "recommended_action": _recommended_action(event_type),
        }


def event_rules():
    return [
        {
            "type": "BATTERY_LOW",
            "condition": "battery_percent <= 20",
            "severity": "WARNING",
            "target_command_type": "CHARGE_PLAN",
            "description": "低电量由车辆状态监控 Agent 自动触发；当前按钮只是手动演示入口。",
        },
        {
            "type": "BATTERY_CRITICAL",
            "condition": "battery_percent <= 10",
            "severity": "CRITICAL",
            "target_command_type": "CHARGE_PLAN",
            "description": "严重低电量会主动提示优先补能，并影响后续导航和车控策略。",
        },
    ]


def _vehicle_state_payload(vehicle_state, network: NetworkStatus = None) -> dict:
    network_status = network or vehicle_state.network
    return {
        "speed_kmh": vehicle_state.speed_kmh,
        "battery_percent": vehicle_state.battery_percent,
        "network": network_status.value,
        "gps": vehicle_state.gps,
        "road_type": vehicle_state.road_type.value,
        "speed_limit_kmh": vehicle_state.speed_limit_kmh,
        "driver_assist_mode": vehicle_state.driver_assist_mode.value,
        "vehicle_ready": vehicle_state.vehicle_ready,
        "lane_confidence": vehicle_state.lane_confidence,
        "safety_state": "正常",
    }


def _severity_for(event_type: str) -> str:
    if event_type == "BATTERY_CRITICAL":
        return "CRITICAL"
    if event_type == "BATTERY_LOW":
        return "WARNING"
    return "INFO"


def _recommended_action(event_type: str) -> str:
    if event_type == "BATTERY_CRITICAL":
        return "请优先前往最近补能点"
    if event_type == "BATTERY_LOW":
        return "建议规划补能点"
    return "请关注车辆状态"


def _event_id(event_type: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{event_type.lower()}-{timestamp}"
