from providers.destination_models import DestinationClarification
from providers.destination_query import looks_like_gps, normalize_destination_query


class ClarificationPolicy:
    def assess(self, query: str, known_destinations=None):
        known_destinations = known_destinations or {}
        normalized = normalize_destination_query(query)
        if not normalized or looks_like_gps(normalized):
            return None
        if normalized in known_destinations:
            return None
        if _is_broad_region(normalized):
            return DestinationClarification(
                normalized,
                "broad_region",
                (
                    "请补充具体目的地，例如商圈、门店、机场、车站或完整地址。",
                    f"如果要去{normalized}的蔚来中心，可以说“导航去{normalized}蔚来中心”。",
                ),
            )
        chain_reason = _chain_poi_clarification_reason(normalized)
        if chain_reason:
            return DestinationClarification(
                normalized,
                chain_reason,
                (
                    "请补充城市或门店所在商圈，例如“上海松江印象城蔚来中心”。",
                    "连锁门店存在多个候选点，系统需要先确认唯一目的地。",
                ),
            )
        if _is_unclear_short_destination(normalized):
            return DestinationClarification(
                normalized,
                "unclear_destination",
                (
                    "请说得更具体一些，例如城市、区县、商圈或完整 POI 名称。",
                    "如果这是地名简称，请补充所在城市后再发起导航。",
                ),
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
