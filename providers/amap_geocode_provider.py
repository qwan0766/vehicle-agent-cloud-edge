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
    confidence: float = 1.0
    quality_reason: str = "not_checked"
    level: str = ""


@dataclass(frozen=True)
class GeocodeQuality:
    confidence: float
    reason: str


class LowConfidenceGeocodeError(RuntimeError):
    def __init__(
        self,
        query: str,
        formatted_address: str,
        gps: str,
        confidence: float,
        reason: str,
        provider_name: str,
    ):
        self.query = query
        self.formatted_address = formatted_address
        self.gps = gps
        self.confidence = confidence
        self.reason = reason
        self.provider_name = provider_name
        super().__init__(
            "AMap geocode low confidence: "
            f"query={query}, formatted_address={formatted_address}, "
            f"confidence={confidence:.2f}, reason={reason}"
        )


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
        formatted_address = first.get("formatted_address", address)
        level = first.get("level", "")
        quality = assess_geocode_quality(address, formatted_address, level=level)
        if quality.confidence < 0.75:
            raise LowConfidenceGeocodeError(
                query=address,
                formatted_address=formatted_address,
                gps=gps,
                confidence=quality.confidence,
                reason=quality.reason,
                provider_name=self.provider_name,
            )
        return GeocodeResult(
            name=address,
            gps=gps,
            formatted_address=formatted_address,
            confidence=quality.confidence,
            quality_reason=quality.reason,
            level=level,
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


def assess_geocode_quality(address: str, formatted_address: str, level: str = "") -> GeocodeQuality:
    query = _normalize_text(address)
    formatted = _normalize_text(formatted_address)
    if not query or not formatted:
        return GeocodeQuality(0.0, "empty_query_or_result")

    if query in formatted:
        return GeocodeQuality(0.98, "query_contained_in_result")

    terms = _significant_terms(query)
    missing_terms = [term for term in terms if not _term_matches(term, formatted)]
    if missing_terms:
        return GeocodeQuality(
            0.35,
            "missing_significant_terms:" + ",".join(missing_terms),
        )

    coverage = _character_coverage(query, formatted)
    if terms and coverage >= 0.65:
        return GeocodeQuality(0.86, "matched_significant_terms")
    if coverage >= 0.82:
        return GeocodeQuality(0.78, "high_character_coverage")
    return GeocodeQuality(coverage, "low_character_coverage")


def _normalize_text(value: str) -> str:
    text = (value or "").strip()
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("的", "")
    for char in " \t\r\n,，。.!！？?:：;；-_/\\()[]【】":
        text = text.replace(char, "")
    return text


def _significant_terms(query: str):
    terms = []
    remainder = query

    for city, _keywords in _CITY_HINTS:
        if city in query:
            terms.append(city)
            remainder = remainder.replace(city, "")

    for phrase in _KNOWN_PLACE_PHRASES:
        if phrase in query:
            terms.append(phrase)
            remainder = remainder.replace(phrase, "")

    if len(remainder) >= 2:
        terms.append(remainder)

    if not terms and query:
        terms.append(query)

    return terms


def _term_matches(term: str, formatted: str) -> bool:
    if term in formatted:
        return True
    aliases = _TERM_ALIASES.get(term, ())
    return any(all(part in formatted for part in alias_parts) for alias_parts in aliases)


def _character_coverage(query: str, formatted: str) -> float:
    unique_query_chars = {char for char in query if char.strip()}
    if not unique_query_chars:
        return 0.0
    matched = {char for char in unique_query_chars if char in formatted}
    return len(matched) / len(unique_query_chars)


_KNOWN_PLACE_PHRASES = (
    "萧山国际机场",
    "萧山机场",
    "蔚来中心",
    "虹桥站",
    "人民广场",
    "东方明珠",
    "静安寺",
    "陆家嘴",
    "外滩",
    "换电站",
    "充电站",
)

_TERM_ALIASES = {
    "萧山机场": (("萧山", "机场"),),
    "虹桥站": (("虹桥", "站"),),
}


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
