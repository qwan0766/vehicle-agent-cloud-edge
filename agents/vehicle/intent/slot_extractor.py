import re
from typing import Dict

from providers.destination_resolver import (
    extract_destination_query,
    normalize_destination_query,
)


class SlotExtractor:
    def extract(self, content: str) -> Dict[str, Dict[str, object]]:
        text = content or ""
        return {
            "navigation": self.navigation_slots(text),
            "car_control": self.car_control_slots(text),
            "info_query": self.info_query_slots(text),
        }

    def navigation_slots(self, content: str) -> Dict[str, object]:
        destination_query = extract_destination_query(content)
        if not destination_query:
            return {}
        return {
            "raw_destination": destination_query,
            "destination_query": normalize_destination_query(destination_query),
        }

    def car_control_slots(self, content: str) -> Dict[str, object]:
        normalized = (content or "").replace(" ", "")
        slots: Dict[str, object] = {}

        temperature = re.search(r"(\d{1,2})\s*(?:度|℃)", content or "")
        if temperature and _contains_any(content, ["温度", "空调"]):
            slots["temperature_c"] = int(temperature.group(1))
            slots["target"] = "cabin_temperature"
            slots["action"] = "set"
            return slots

        if _contains_any(content, ["座椅加热"]):
            slots["target"] = "seat_heat"
            if _contains_any(content, ["打开", "开启", "启动"]):
                slots["action"] = "on"
                return slots
            if _contains_any(content, ["关闭", "关掉"]):
                slots["action"] = "off"
                return slots

        cabin_targets = ("空调", "车窗", "后备箱", "雨刷", "车灯", "座椅")
        action_words = ("打开", "开启", "关闭", "关掉", "调到", "调低", "调高")
        if any(target in normalized for target in cabin_targets) and any(
            action in normalized for action in action_words
        ):
            slots["target"] = "cabin_device"
            slots["action"] = "control"
            return slots
        return slots

    def info_query_slots(self, content: str) -> Dict[str, object]:
        normalized = (content or "").replace(" ", "")
        topics = (
            "AEB",
            "自动紧急制动",
            "制动距离",
            "能耗",
            "续航",
            "换电",
            "充电",
            "电池",
            "胎压",
            "安全气囊",
        )
        for topic in topics:
            if topic.lower() in normalized.lower():
                return {"topic": topic}
        return {}


def _contains_any(content: str, keywords) -> bool:
    normalized = (content or "").lower()
    return any(keyword.lower() in normalized for keyword in keywords)
