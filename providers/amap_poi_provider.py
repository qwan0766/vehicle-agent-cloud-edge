import json
from urllib import parse, request

from providers.offline_charge_provider import ChargeStation


class AmapPOIProvider:
    provider_name = "amap_poi"

    def __init__(self, api_key: str, timeout: int = 10, transport=None):
        if not api_key:
            raise ValueError("AMap api_key is required")
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport or _get_json

    def build_around_search_url(self, gps: str, limit: int = 3, radius: int = 10000) -> str:
        query = parse.urlencode(
            {
                "key": self.api_key,
                "location": _normalize_gps(gps),
                "radius": radius,
                "types": "011100",
                "offset": limit,
                "page": 1,
                "extensions": "all",
                "output": "JSON",
            }
        )
        return f"https://restapi.amap.com/v3/place/around?{query}"

    def find_nearby(self, gps: str, limit: int = 3):
        payload = self.transport(self.build_around_search_url(gps, limit=limit), self.timeout)
        if payload.get("status") != "1":
            raise RuntimeError(f"AMap POI error: {payload.get('info', 'UNKNOWN')}")
        stations = []
        for item in payload.get("pois", [])[:limit]:
            distance_m = float(item.get("distance") or 0)
            stations.append(
                ChargeStation(
                    name=item.get("name", "高德充电站"),
                    distance_km=round(distance_m / 1000, 2),
                    status=_station_status(item),
                    estimated_minutes=30,
                )
            )
        return stations


def _normalize_gps(gps: str) -> str:
    longitude, latitude = [part.strip() for part in gps.split(",", 1)]
    return f"{longitude},{latitude}"


def _station_status(item: dict) -> str:
    biz_ext = item.get("biz_ext") or {}
    rating = biz_ext.get("rating")
    if rating:
        return f"可用，评分{rating}"
    return "可用"


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
