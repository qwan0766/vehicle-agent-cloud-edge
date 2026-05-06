from dataclasses import dataclass
import json
from urllib import parse, request


_CITY_HINTS = (
    (
        "\u5317\u4eac",
        (
            "\u5317\u4eac",
            "\u5929\u5b89\u95e8",
            "\u4e2d\u5173\u6751",
            "\u671d\u9633",
            "\u671b\u4eac",
            "\u5317\u4eac\u851a\u6765\u4e2d\u5fc3",
        ),
    ),
    (
        "\u4e0a\u6d77",
        (
            "\u4e0a\u6d77",
            "\u5916\u6ee9",
            "\u8679\u6865",
            "\u4eba\u6c11\u5e7f\u573a",
            "\u4e1c\u65b9\u660e\u73e0",
            "\u9646\u5bb6\u5634",
            "\u6d66\u4e1c",
            "\u9759\u5b89\u5bfa",
            "\u5f90\u5bb6\u6c47",
            "\u5357\u4eac\u8def",
            "\u851a\u6765\u4e2d\u5fc3",
        ),
    ),
    (
        "\u676d\u5dde",
        (
            "\u676d\u5dde",
            "\u8427\u5c71",
            "\u897f\u6e56",
            "\u676d\u5dde\u4e1c\u7ad9",
            "\u6ee8\u6c5f",
            "\u7075\u9690",
        ),
    ),
)


@dataclass(frozen=True)
class GeocodeResult:
    name: str
    gps: str
    formatted_address: str


class AmapGeocodeProvider:
    provider_name = "amap_geocode"

    def __init__(self, api_key: str, city: str = "", timeout: int = 10, transport=None):
        if not api_key:
            raise ValueError("AMap api_key is required")
        self.api_key = api_key
        self.city = city
        self.timeout = timeout
        self.transport = transport or _get_json

    def build_geocode_url(self, address: str) -> str:
        params = {
            "key": self.api_key,
            "address": address,
            "output": "JSON",
        }
        city = self.city or _infer_city(address)
        if city:
            params["city"] = city
        query = parse.urlencode(params)
        return f"https://restapi.amap.com/v3/geocode/geo?{query}"

    def geocode(self, address: str) -> GeocodeResult:
        payload = self.transport(self.build_geocode_url(address), self.timeout)
        if payload.get("status") != "1":
            raise RuntimeError(f"AMap geocode error: {payload.get('info', 'UNKNOWN')}")
        geocodes = payload.get("geocodes") or []
        if not geocodes:
            raise RuntimeError(f"AMap geocode returned no result: {address}")

        first = geocodes[0]
        gps = first.get("location", "")
        if not gps:
            raise RuntimeError(f"AMap geocode returned empty location: {address}")
        return GeocodeResult(
            name=address,
            gps=gps,
            formatted_address=first.get("formatted_address", address),
        )


def _infer_city(address: str) -> str:
    normalized = (address or "").strip()
    if not normalized:
        return ""

    for city, _keywords in _CITY_HINTS:
        if city in normalized:
            return city

    for city, keywords in _CITY_HINTS:
        if any(keyword in normalized for keyword in keywords):
            return city
    return ""


def _get_json(url: str, timeout: int):
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "weilai-agent-online-demo/1.0",
        },
        method="GET",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
