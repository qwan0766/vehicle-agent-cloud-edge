from urllib import parse

from providers.errors import ProviderBadResponseError
from providers.http import get_json
from providers.offline_charge_provider import ChargeStation
from providers.destination_models import DestinationCandidate


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

    def build_text_search_url(self, keyword: str, city: str = "", limit: int = 3) -> str:
        params = {
            "key": self.api_key,
            "keywords": keyword,
            "offset": limit,
            "page": 1,
            "extensions": "all",
            "output": "JSON",
        }
        if city:
            params["city"] = city
            params["citylimit"] = "true"
        query = parse.urlencode(params)
        return f"https://restapi.amap.com/v3/place/text?{query}"

    def find_nearby(self, gps: str, limit: int = 3):
        payload = self.transport(self.build_around_search_url(gps, limit=limit), self.timeout)
        if payload.get("status") != "1":
            raise ProviderBadResponseError(
                f"AMap POI error: {payload.get('info', 'UNKNOWN')}",
                provider=self.provider_name,
                operation="place_around",
                code=payload.get("infocode") or payload.get("info") or "AMAP_POI_ERROR",
            )
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

    def search_text(self, keyword: str, city: str = "", limit: int = 3):
        payload = self.transport(
            self.build_text_search_url(keyword, city=city, limit=limit),
            self.timeout,
        )
        if payload.get("status") != "1":
            raise ProviderBadResponseError(
                f"AMap POI text error: {payload.get('info', 'UNKNOWN')}",
                provider=self.provider_name,
                operation="place_text",
                code=payload.get("infocode") or payload.get("info") or "AMAP_POI_TEXT_ERROR",
            )
        candidates = []
        for item in payload.get("pois", [])[:limit]:
            location = item.get("location", "")
            candidates.append(
                DestinationCandidate(
                    name=item.get("name", keyword),
                    gps=location,
                    address=item.get("address") or item.get("pname", ""),
                    source=self.provider_name,
                    confidence=_poi_confidence(keyword, item),
                    distance_km=_distance_km(item),
                    reason="provider_text_search",
                )
            )
        return candidates


def _normalize_gps(gps: str) -> str:
    longitude, latitude = [part.strip() for part in gps.split(",", 1)]
    return f"{longitude},{latitude}"


def _station_status(item: dict) -> str:
    biz_ext = item.get("biz_ext") or {}
    rating = biz_ext.get("rating")
    if rating:
        return f"可用，评分{rating}"
    return "可用"


def _distance_km(item: dict):
    distance = item.get("distance")
    if not distance:
        return None
    try:
        return round(float(distance) / 1000, 2)
    except (TypeError, ValueError):
        return None


def _poi_confidence(keyword: str, item: dict) -> float:
    name = item.get("name", "")
    address = item.get("address", "")
    city = item.get("cityname", "")
    text = f"{name}{address}{city}"
    if keyword and keyword in text:
        return 0.9
    keyword_chars = {char for char in keyword if char.strip()}
    if not keyword_chars:
        return 0.0
    matched = {char for char in keyword_chars if char in text}
    return round(len(matched) / len(keyword_chars), 2)


def _get_json(url: str, timeout: int):
    return get_json(
        url,
        timeout,
        provider=AmapPOIProvider.provider_name,
        operation="place",
        headers={
            "User-Agent": "weilai-agent-offline-demo/1.0",
        },
    )
