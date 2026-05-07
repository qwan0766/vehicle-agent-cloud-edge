from dataclasses import replace
from threading import RLock

from core.constants import DriverAssistMode, NetworkStatus, RoadType
from data.vehicle_state import DEFAULT_VEHICLE_STATE, VehicleState


class VehicleStateService:
    def __init__(self, initial_state: VehicleState = DEFAULT_VEHICLE_STATE):
        self._initial_state = initial_state
        self._state = initial_state
        self._lock = RLock()

    def current_state(self) -> VehicleState:
        with self._lock:
            return self._state

    def reset(self) -> VehicleState:
        with self._lock:
            self._state = self._initial_state
            return self._state

    def update(self, updates: dict) -> VehicleState:
        payload = updates or {}
        with self._lock:
            self._state = replace(
                self._state,
                speed_kmh=_bounded_int(
                    payload,
                    "speed_kmh",
                    self._state.speed_kmh,
                    minimum=0,
                    maximum=240,
                ),
                battery_percent=_bounded_int(
                    payload,
                    "battery_percent",
                    self._state.battery_percent,
                    minimum=0,
                    maximum=100,
                ),
                gps=str(payload.get("gps", self._state.gps)).strip() or self._state.gps,
                road_type=_parse_enum(
                    RoadType,
                    payload.get("road_type"),
                    self._state.road_type,
                ),
                speed_limit_kmh=_bounded_int(
                    payload,
                    "speed_limit_kmh",
                    self._state.speed_limit_kmh,
                    minimum=0,
                    maximum=160,
                ),
                driver_assist_mode=_parse_enum(
                    DriverAssistMode,
                    payload.get("driver_assist_mode"),
                    self._state.driver_assist_mode,
                ),
                vehicle_ready=bool(payload.get("vehicle_ready", self._state.vehicle_ready)),
                lane_confidence=_bounded_float(
                    payload,
                    "lane_confidence",
                    self._state.lane_confidence,
                    minimum=0.0,
                    maximum=1.0,
                ),
            )
            return self._state

    def to_payload(self, network: NetworkStatus = None) -> dict:
        state = self.current_state()
        network_status = network or state.network
        return {
            "speed_kmh": state.speed_kmh,
            "battery_percent": state.battery_percent,
            "network": network_status.value,
            "gps": state.gps,
            "road_type": state.road_type.value,
            "speed_limit_kmh": state.speed_limit_kmh,
            "driver_assist_mode": state.driver_assist_mode.value,
            "vehicle_ready": state.vehicle_ready,
            "lane_confidence": state.lane_confidence,
            "safety_state": "正常",
        }


def _parse_enum(enum_cls, value, fallback):
    if value is None:
        return fallback
    try:
        return enum_cls(str(value).upper())
    except ValueError:
        return fallback


def _bounded_int(payload, key: str, fallback: int, minimum: int, maximum: int) -> int:
    try:
        value = int(payload.get(key, fallback))
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, value))


def _bounded_float(payload, key: str, fallback: float, minimum: float, maximum: float) -> float:
    try:
        value = float(payload.get(key, fallback))
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, value))
