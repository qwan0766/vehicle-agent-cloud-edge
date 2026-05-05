from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DestinationResolution:
    name: str
    gps: str
    source: str


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
    for keyword, resolution in KNOWN_DESTINATIONS.items():
        if keyword in normalized:
            return resolution

    if _looks_like_gps(normalized):
        return DestinationResolution(normalized, normalized, "explicit_gps")

    query = extract_destination_query(normalized)
    if not query:
        raise ValueError(f"无法从指令中解析目的地：{content}")

    if _looks_like_gps(query):
        return DestinationResolution(query, query, "explicit_gps")

    if geocoder is None:
        raise ValueError(f"未知目的地且未配置在线地理编码：{query}")

    geocode_result = geocoder.geocode(query)
    return DestinationResolution(
        name=geocode_result.name or query,
        gps=geocode_result.gps,
        source=geocoder.provider_name,
    )


def extract_destination_query(content: str) -> str:
    text = re.sub(r"[，。！？!?.\s]+$", "", (content or "").strip())
    for prefix in NAVIGATION_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return ""


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
