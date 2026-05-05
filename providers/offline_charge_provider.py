from dataclasses import dataclass


@dataclass(frozen=True)
class ChargeStation:
    name: str
    distance_km: float
    status: str
    estimated_minutes: int


class OfflineChargeProvider:
    provider_name = "offline_charge"

    def __init__(self):
        self._stations = [
            ChargeStation("蔚来换电站 上海中心", 1.8, "空闲", 3),
            ChargeStation("蔚来超充站 陆家嘴", 3.6, "少量排队", 18),
            ChargeStation("公共快充站 世纪大道", 4.2, "空闲", 30),
        ]

    def find_nearby(self, gps: str, limit: int = 3):
        return sorted(self._stations, key=lambda station: station.distance_km)[:limit]
