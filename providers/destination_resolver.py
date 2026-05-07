from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DestinationResolution:
    name: str
    gps: str
    source: str


class DestinationClarificationRequired(ValueError):
    def __init__(self, query: str, reason: str, suggestions=None):
        self.query = query
        self.reason = reason
        self.suggestions = list(suggestions or [])
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

NAVIGATION_PREFIXES = (
    "帮我导航到",
    "帮我导航去",
    "导航到",
    "导航去",
    "我要去",
    "我想去",
    "开车去",
    "去",
    "到",
)


def resolve_destination(content: str, geocoder=None) -> str:
    return resolve_destination_detail(content, geocoder=geocoder).gps


def resolve_destination_detail(content: str, geocoder=None) -> DestinationResolution:
    normalized = (content or "").strip()
    if _looks_like_gps(normalized):
        return DestinationResolution(normalized, normalized, "explicit_gps")

    query = extract_destination_query(normalized)
    if query:
        query = normalize_destination_query(query)
        if _looks_like_gps(query):
            return DestinationResolution(query, query, "explicit_gps")

        if query in KNOWN_DESTINATIONS:
            return KNOWN_DESTINATIONS[query]

        clarification = assess_destination_clarification(query)
        if clarification:
            raise clarification

        if geocoder is None:
            raise ValueError(f"未知目的地且未配置在线地理编码：{query}")

        geocode_result = geocoder.geocode(query)
        return DestinationResolution(
            name=geocode_result.name or query,
            gps=geocode_result.gps,
            source=geocoder.provider_name,
        )

    for keyword, resolution in KNOWN_DESTINATIONS.items():
        if keyword in normalized:
            return resolution

    if not query:
        raise ValueError(f"无法从指令中解析目的地：{content}")


def extract_destination_query(content: str) -> str:
    text = re.sub(r"[，。！？!?.\s]+$", "", (content or "").strip())
    for prefix in NAVIGATION_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return ""


def normalize_destination_query(query: str) -> str:
    text = re.sub(r"\s+", "", (query or "").strip())
    text = re.sub(r"^(.{2,8}?)(?:的)(蔚来中心|换电站|充电站)$", r"\1\2", text)
    return text


def assess_destination_clarification(query: str):
    normalized = normalize_destination_query(query)
    if not normalized or _looks_like_gps(normalized):
        return None
    if normalized in KNOWN_DESTINATIONS:
        return None
    if _is_broad_region(normalized):
        return DestinationClarificationRequired(
            normalized,
            "broad_region",
            [
                "请补充具体目的地，例如商圈、门店、机场、车站或完整地址。",
                f"如果要去{normalized}的蔚来中心，可以说“导航去{normalized}蔚来中心”。",
            ],
        )
    chain_reason = _chain_poi_clarification_reason(normalized)
    if chain_reason:
        return DestinationClarificationRequired(
            normalized,
            chain_reason,
            [
                "请补充城市或门店所在商圈，例如“上海松江印象城蔚来中心”。",
                "连锁门店存在多个候选点，系统需要先确认唯一目的地。",
            ],
        )
    if _is_unclear_short_destination(normalized):
        return DestinationClarificationRequired(
            normalized,
            "unclear_destination",
            [
                "请说得更具体一些，例如城市、区县、商圈或完整 POI 名称。",
                "如果这是地名简称，请补充所在城市后再发起导航。",
            ],
        )
    return None


def _is_broad_region(query: str) -> bool:
    return query in _BROAD_REGION_NAMES


def _chain_poi_clarification_reason(query: str) -> str:
    for phrase in _CHAIN_POI_PHRASES:
        if query == phrase:
            return ""
        if query.endswith(phrase):
            qualifier = query[: -len(phrase)]
            if qualifier and not _contains_known_region_or_venue(qualifier):
                return "unknown_chain_poi_qualifier"
    return ""


def _is_unclear_short_destination(query: str) -> bool:
    if query in _KNOWN_SHORT_POIS:
        return False
    if _contains_known_region_or_venue(query):
        return False
    if any(marker in query for marker in _ADDRESS_CONFIDENCE_MARKERS):
        return False
    return len(query) <= 4


def _contains_known_region_or_venue(query: str) -> bool:
    return any(term in query for term in _KNOWN_REGIONS_AND_VENUES)


def _looks_like_gps(content: str) -> bool:
    if "," not in content:
        return False
    left, right = [part.strip() for part in content.split(",", 1)]
    try:
        float(left)
        float(right)
    except ValueError:
        return False
    return True


_BROAD_REGION_NAMES = {
    "北京",
    "北京市",
    "上海",
    "上海市",
    "杭州",
    "杭州市",
    "广州",
    "广州市",
    "深圳",
    "深圳市",
    "南京",
    "南京市",
    "苏州",
    "苏州市",
    "成都",
    "成都市",
    "重庆",
    "重庆市",
    "中国",
}

_CHAIN_POI_PHRASES = (
    "蔚来中心",
    "换电站",
    "充电站",
)

_KNOWN_SHORT_POIS = {
    "外滩",
    "陆家嘴",
    "静安寺",
    "东方明珠",
    "人民广场",
    "西湖",
}

_KNOWN_REGIONS_AND_VENUES = {
    "北京",
    "上海",
    "杭州",
    "广州",
    "深圳",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "松江",
    "东城",
    "朝阳",
    "望京",
    "黄浦",
    "浦东",
    "虹桥",
    "萧山",
    "西湖",
    "滨江",
    "印象城",
    "东方广场",
}

_ADDRESS_CONFIDENCE_MARKERS = (
    "机场",
    "车站",
    "火车站",
    "高铁站",
    "地铁站",
    "大厦",
    "广场",
    "商场",
    "医院",
    "学校",
    "公园",
    "酒店",
    "中心",
    "路",
    "街",
    "区",
    "园",
    "馆",
    "塔",
    "寺",
    "城",
)
