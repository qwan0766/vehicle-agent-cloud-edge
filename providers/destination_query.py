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


def looks_like_gps(content: str) -> bool:
    if "," not in content:
        return False
    left, right = [part.strip() for part in content.split(",", 1)]
    try:
        float(left)
        float(right)
    except ValueError:
        return False
    return True
