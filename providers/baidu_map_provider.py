from urllib import parse

from providers.errors import ProviderBadResponseError
from providers.http import get_json
from providers.offline_map_provider import RouteSummary


class BaiduMapProvider:
    provider_name = "baidu_map"

    def __init__(self, api_key: str, timeout: int = 10, transport=None):
        if not api_key:
            raise ValueError("Baidu map api_key is required")
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport or _get_json

    def build_driving_route_url(self, origin: str, destination: str) -> str:
        query = parse.urlencode(
            {
                "origin": origin,
                "destination": destination,
                "ak": self.api_key,
            }
        )
        return f"https://api.map.baidu.com/direction/v2/driving?{query}"

    def plan_route(self, origin: str, destination: str, preference: str = "") -> RouteSummary:
        payload = self.transport(self.build_driving_route_url(origin, destination), self.timeout)
        if payload.get("status") not in {0, "0", None} and not payload.get("result"):
            raise ProviderBadResponseError(
                f"Baidu route error: {payload.get('message', 'UNKNOWN')}",
                provider=self.provider_name,
                operation="driving_route",
                code=str(payload.get("status") or "BAIDU_ROUTE_ERROR"),
            )
        routes = payload.get("result", {}).get("routes") or []
        if not routes:
            raise ProviderBadResponseError(
                "Baidu route returned no route",
                provider=self.provider_name,
                operation="driving_route",
                code="BAIDU_ROUTE_EMPTY_PATH",
            )
        route = routes[0]
        distance_km = round(float(route.get("distance", 0)) / 1000, 1)
        duration_minutes = round(float(route.get("duration", 0)) / 60)
        return RouteSummary(
            provider=self.provider_name,
            origin=origin,
            destination=destination,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            strategy=preference or "时间优先",
        )


def _get_json(url: str, timeout: int):
    return get_json(
        url,
        timeout,
        provider=BaiduMapProvider.provider_name,
        operation="driving_route",
    )
