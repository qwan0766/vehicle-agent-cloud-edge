from urllib import parse

from providers.errors import ProviderBadResponseError
from providers.http import get_json
from providers.offline_charge_provider import ChargeStation


class OpenChargeMapProvider:
    provider_name = "open_charge_map"

    def __init__(self, api_key: str = "", timeout: int = 10, transport=None):
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport or _get_json

    def build_poi_url(self, gps: str, limit: int = 3) -> str:
        longitude, latitude = _parse_gps(gps)
        query = {
            "latitude": latitude,
            "longitude": longitude,
            "distance": 10,
            "distanceunit": "KM",
            "maxresults": limit,
            "output": "json",
        }
        if self.api_key:
            query["key"] = self.api_key
        return f"https://api.openchargemap.io/v3/poi?{parse.urlencode(query)}"

    def find_nearby(self, gps: str, limit: int = 3):
        payload = self.transport(self.build_poi_url(gps, limit=limit), self.timeout)
        if not isinstance(payload, list):
            raise ProviderBadResponseError(
                "OpenChargeMap returned invalid payload",
                provider=self.provider_name,
                operation="poi",
                code="OPENCHARGEMAP_INVALID_PAYLOAD",
            )
        stations = []
        for item in payload[:limit]:
            address = item.get("AddressInfo", {})
            status = item.get("StatusType", {}).get("Title", "未知")
            stations.append(
                ChargeStation(
                    name=address.get("Title", "OpenChargeMap 充电站"),
                    distance_km=round(float(address.get("Distance", 0)), 1),
                    status=status,
                    estimated_minutes=30,
                )
            )
        return stations


def _parse_gps(gps: str):
    lon, lat = [part.strip() for part in gps.split(",", 1)]
    return lon, lat


def _get_json(url: str, timeout: int):
    return get_json(
        url,
        timeout,
        provider=OpenChargeMapProvider.provider_name,
        operation="poi",
        headers={
            "User-Agent": "weilai-agent-offline-demo/1.0",
        },
    )
