from providers.amap_geocode_provider import LowConfidenceGeocodeError
from providers.destination_clarification_policy import ClarificationPolicy
from providers.destination_models import DestinationCandidate, DestinationResolution
from providers.destination_query import (
    extract_destination_query,
    looks_like_gps,
    normalize_destination_query,
)


class DestinationClarificationRequired(ValueError):
    def __init__(self, query: str, reason: str, suggestions=None, candidates=None):
        self.query = query
        self.reason = reason
        self.suggestions = list(suggestions or [])
        self.candidates = list(candidates or [])
        super().__init__(
            f"Destination clarification required: query={query}, reason={reason}"
        )


KNOWN_DESTINATIONS = {
    "导航去蔚来中心": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "蔚来中心": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "我要回家": DestinationResolution("家", "121.42,31.20", "builtin"),
    "回家": DestinationResolution("家", "121.42,31.20", "builtin"),
    "电量低": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "补能": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "充电规划": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "换电站": DestinationResolution("附近补能点", "121.481,31.231", "builtin"),
    "我的偏好": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "用户画像": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
    "个性化偏好": DestinationResolution("蔚来中心", "121.50,31.25", "builtin"),
}


class DestinationResolver:
    def __init__(self, known_destinations=None, clarification_policy=None):
        self.known_destinations = known_destinations or KNOWN_DESTINATIONS
        self.clarification_policy = clarification_policy or ClarificationPolicy()

    def resolve(self, content: str, geocoder=None) -> DestinationResolution:
        normalized = (content or "").strip()
        if looks_like_gps(normalized):
            return DestinationResolution(normalized, normalized, "explicit_gps")

        query = extract_destination_query(normalized)
        if query:
            return self._resolve_query(query, geocoder=geocoder)

        for keyword, resolution in self.known_destinations.items():
            if keyword in normalized:
                return resolution
        raise ValueError(f"无法从指令中解析目的地：{content}")

    def _resolve_query(self, query: str, geocoder=None) -> DestinationResolution:
        normalized_query = normalize_destination_query(query)
        if looks_like_gps(normalized_query):
            return DestinationResolution(
                normalized_query,
                normalized_query,
                "explicit_gps",
            )
        if normalized_query in self.known_destinations:
            return self.known_destinations[normalized_query]

        clarification = self.clarification_policy.assess(
            normalized_query,
            known_destinations=self.known_destinations,
        )
        if clarification:
            raise DestinationClarificationRequired(
                clarification.query,
                clarification.reason,
                suggestions=clarification.suggestions,
                candidates=[item.to_payload() for item in clarification.candidates],
            )

        if geocoder is None:
            raise ValueError(f"未知目的地且未配置在线地理编码：{normalized_query}")

        try:
            geocode_result = geocoder.geocode(normalized_query)
        except LowConfidenceGeocodeError as exc:
            candidate = DestinationCandidate(
                name=exc.formatted_address,
                gps=exc.gps,
                address=exc.formatted_address,
                source=exc.provider_name,
                confidence=exc.confidence,
                reason=exc.reason,
            )
            raise DestinationClarificationRequired(
                normalized_query,
                "low_confidence_provider_result",
                suggestions=("请确认是否选择该候选地点，或补充城市、商圈、完整门店名称。",),
                candidates=[candidate.to_payload()],
            ) from exc

        return DestinationResolution(
            name=geocode_result.name or normalized_query,
            gps=geocode_result.gps,
            source=geocoder.provider_name,
            confidence=getattr(geocode_result, "confidence", 1.0),
        )
