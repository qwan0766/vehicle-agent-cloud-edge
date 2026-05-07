import re


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

NON_REFINEMENT_KEYWORDS = (
    "导航",
    "温度",
    "座椅",
    "空调",
    "音乐",
    "音量",
    "打开",
    "关闭",
    "电量",
    "充电",
    "换电",
    "偏好",
    "画像",
    "AEB",
    "动力",
    "制动",
    "转向",
    "加速",
    "刹车",
)

DEFAULT_SUGGESTIONS = {
    "broad_region": [
        "请补充具体地点，例如城市中的商圈、门店、机场、车站或完整地址。",
        "如果要去某个蔚来中心，可以输入“导航去北京东方广场蔚来中心”。",
    ],
    "unknown_chain_poi_qualifier": [
        "请补充城市或门店所在商圈，例如“上海松江印象城蔚来中心”。",
        "连锁门店可能有多个候选点，确认唯一目的地后再开始导航。",
    ],
    "unclear_destination": [
        "请说得更具体一些，例如城市、区县、商圈或完整 POI 名称。",
        "如果这是地点简称，请补充所在城市后再发起导航。",
    ],
    "low_confidence_provider_result": [
        "候选地点置信度较低，请确认是否选择该地点。",
        "也可以补充城市、商圈、完整门店名称或完整地址。",
    ],
    "destination_candidate_confirmation": [
        "地图返回了多个可能地点，请先确认唯一目的地。",
        "也可以补充城市、商圈、完整门店名称或完整地址。",
    ],
}

QUESTIONS = {
    "broad_region": "我还不能确认唯一目的地。请补充更具体的城市内地点、商圈、门店或完整地址。",
    "unknown_chain_poi_qualifier": "这个门店名称不够明确，可能匹配到错误地点。请补充城市、商圈或完整门店名称。",
    "unclear_destination": "这个目的地信息还不够具体。请补充城市、区县、商圈或完整 POI 名称。",
    "low_confidence_provider_result": "地图返回了低置信度候选地点。为了避免导航到错误位置，请先确认目的地。",
    "destination_candidate_confirmation": "我找到了可能的目的地，但还不能确定哪一个就是你想去的地方。请先选择候选地点或补充更完整的信息。",
}


def build_destination_clarification(exc, original_content: str) -> dict:
    reason = getattr(exc, "reason", "") or "unclear_destination"
    query = getattr(exc, "query", "") or _extract_query_fallback(original_content)
    suggestions = list(getattr(exc, "suggestions", None) or [])
    if not suggestions:
        suggestions = list(DEFAULT_SUGGESTIONS.get(reason, DEFAULT_SUGGESTIONS["unclear_destination"]))

    return {
        "type": "destination",
        "query": query,
        "reason": reason,
        "question": QUESTIONS.get(reason, QUESTIONS["unclear_destination"]),
        "suggestions": suggestions,
        "candidates": list(getattr(exc, "candidates", None) or []),
        "original_content": original_content,
    }


def is_destination_refinement(content: str, pending: dict) -> bool:
    if not pending or pending.get("type") != "destination":
        return False

    text = (content or "").strip()
    if not text:
        return False
    if any(text.startswith(prefix) for prefix in NAVIGATION_PREFIXES):
        return False
    if any(keyword in text for keyword in NON_REFINEMENT_KEYWORDS):
        return False
    return True


def reconstruct_destination_command(content: str, pending: dict) -> str:
    text = _strip_terminal_punctuation(content)
    original = _strip_terminal_punctuation(pending.get("original_content", ""))
    query = pending.get("query", "")
    if not original:
        return f"导航去{query}{text}"
    if query and original.endswith(query):
        return f"{original}{text}"
    return f"{original}{text}"


def _extract_query_fallback(content: str) -> str:
    text = _strip_terminal_punctuation(content)
    for prefix in NAVIGATION_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _strip_terminal_punctuation(content: str) -> str:
    return re.sub(r"[\s，。！？,.!?]+$", "", (content or "").strip())
