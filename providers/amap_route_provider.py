import json
from urllib import parse, request

from providers.offline_map_provider import RouteSummary


class AmapRouteProvider:
    provider_name = "amap_route"

    def __init__(self, api_key: str, timeout: int = 10, transport=None):
        if not api_key:
            raise ValueError("AMap api_key is required")
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport or _get_json

    def build_driving_route_url(self, origin: str, destination: str, preference: str = "") -> str:
        query = parse.urlencode(
            {
                "key": self.api_key,
                "origin": _normalize_gps(origin),
                "destination": _normalize_gps(destination),
                "strategy": _strategy_code(preference),
                "extensions": "base",
                "output": "JSON",
            }
        )
        return f"https://restapi.amap.com/v3/direction/driving?{query}"

    def plan_route(self, origin: str, destination: str, preference: str = "") -> RouteSummary:
        payload = self.transport(
            self.build_driving_route_url(origin, destination, preference=preference),
            self.timeout,
        )
        if payload.get("status") != "1":
            raise RuntimeError(f"AMap route error: {payload.get('info', 'UNKNOWN')}")
        path = payload.get("route", {}).get("paths", [{}])[0]
        distance_km = round(float(path.get("distance") or 0) / 1000, 1)
        duration_minutes = round(float(path.get("duration") or 0) / 60)
        return RouteSummary(
            provider=self.provider_name,
            origin=origin,
            destination=destination,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            strategy="高速优先" if preference == "高速" else "时间优先",
        )


def _strategy_code(preference: str) -> int:
    if preference == "高速":
        return 10
    return 0


def _normalize_gps(gps: str) -> str:
    longitude, latitude = [part.strip() for part in gps.split(",", 1)]
    return f"{longitude},{latitude}"


def _get_json(url: str, timeout: int):
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "weilai-agent-offline-demo/1.0",
        },
        method="GET",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
