KNOWN_DESTINATIONS = {
    "导航去蔚来中心": "121.50,31.25",
    "蔚来中心": "121.50,31.25",
    "我要回家": "121.42,31.20",
    "回家": "121.42,31.20",
    "电量低": "121.481,31.231",
    "我的偏好": "121.50,31.25",
}


def resolve_destination(content: str) -> str:
    for keyword, gps in KNOWN_DESTINATIONS.items():
        if keyword in content:
            return gps
    if "," in content:
        return content
    return "121.50,31.25"
