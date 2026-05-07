from dataclasses import dataclass

from core.constants import DriverAssistMode, NetworkStatus, RoadType


@dataclass(frozen=True)
class VehicleState:
    speed_kmh: int
    battery_percent: int
    network: NetworkStatus
    gps: str
    road_type: RoadType = RoadType.HIGHWAY
    speed_limit_kmh: int = 120
    driver_assist_mode: DriverAssistMode = DriverAssistMode.ACC
    vehicle_ready: bool = True
    lane_confidence: float = 0.92


DEFAULT_VEHICLE_STATE = VehicleState(
    speed_kmh=60,
    battery_percent=35,
    network=NetworkStatus.ONLINE,
    gps="121.48, 31.23",
    road_type=RoadType.HIGHWAY,
    speed_limit_kmh=120,
    driver_assist_mode=DriverAssistMode.ACC,
    vehicle_ready=True,
    lane_confidence=0.92,
)
