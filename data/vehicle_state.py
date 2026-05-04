from dataclasses import dataclass

from core.constants import NetworkStatus


@dataclass(frozen=True)
class VehicleState:
    speed_kmh: int
    battery_percent: int
    network: NetworkStatus
    gps: str


DEFAULT_VEHICLE_STATE = VehicleState(
    speed_kmh=60,
    battery_percent=35,
    network=NetworkStatus.ONLINE,
    gps="121.48, 31.23",
)
