from dataclasses import dataclass


@dataclass(frozen=True)
class RouteSummary:
    provider: str
    origin: str
    destination: str
    distance_km: float
    duration_minutes: int
    strategy: str

    def to_text(self) -> str:
        return (
            f"{self.provider}路线：预计{self.distance_km}km，"
            f"{self.duration_minutes}分钟，策略{self.strategy}"
        )


class OfflineMapProvider:
    provider_name = "offline_map"

    def plan_route(self, origin: str, destination: str, preference: str = "") -> RouteSummary:
        strategy = "高速优先" if preference == "高速" else "时间优先"
        return RouteSummary(
            provider=self.provider_name,
            origin=origin,
            destination=destination,
            distance_km=12.8,
            duration_minutes=28,
            strategy=strategy,
        )
