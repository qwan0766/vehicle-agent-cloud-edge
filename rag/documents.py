from dataclasses import dataclass
from typing import Dict, List

from core.constants import CommandType


@dataclass(frozen=True)
class RetrievalDocument:
    doc_id: str
    text: str
    keywords: List[str]
    metadata: Dict[str, object]


INTENT_DOCUMENTS = [
    RetrievalDocument(
        doc_id="intent_nav_nio_center",
        text="导航去蔚来中心",
        keywords=["导航", "蔚来中心", "路线", "去"],
        metadata={"command_type": CommandType.NAVIGATION},
    ),
    RetrievalDocument(
        doc_id="intent_nav_home",
        text="我要回家",
        keywords=["回家", "导航", "家"],
        metadata={"command_type": CommandType.NAVIGATION},
    ),
    RetrievalDocument(
        doc_id="intent_seat_heat",
        text="打开座椅加热",
        keywords=["座椅加热", "打开", "车控", "加热"],
        metadata={"command_type": CommandType.CAR_CONTROL},
    ),
    RetrievalDocument(
        doc_id="intent_temperature",
        text="温度调到24度",
        keywords=["温度", "24度", "空调", "车控"],
        metadata={"command_type": CommandType.CAR_CONTROL},
    ),
    RetrievalDocument(
        doc_id="intent_charge_plan",
        text="电量低",
        keywords=["电量低", "补能", "充电", "换电"],
        metadata={"command_type": CommandType.CHARGE_PLAN},
    ),
    RetrievalDocument(
        doc_id="intent_personalize",
        text="我的偏好",
        keywords=["偏好", "用户画像", "个性化"],
        metadata={"command_type": CommandType.PERSONALIZE},
    ),
]


ROUTE_DOCUMENTS = [
    RetrievalDocument(
        doc_id="route_low_battery_swap",
        text="电量低于20%建议前往换电站",
        keywords=["电量低", "20%", "换电站", "补能", "充电"],
        metadata={"topic": "charge_plan"},
    ),
    RetrievalDocument(
        doc_id="route_highway_preference",
        text="长途优先高速路线",
        keywords=["长途", "高速", "导航", "路线", "蔚来中心"],
        metadata={"topic": "navigation"},
    ),
    RetrievalDocument(
        doc_id="route_comfort_temperature",
        text="车内舒适温度22~25℃",
        keywords=["温度", "舒适", "22", "25", "空调"],
        metadata={"topic": "comfort"},
    ),
    RetrievalDocument(
        doc_id="route_swap_duration",
        text="换电站约3分钟完成换电",
        keywords=["换电站", "3分钟", "换电", "补能"],
        metadata={"topic": "charge_plan"},
    ),
    RetrievalDocument(
        doc_id="route_offline_navigation",
        text="断网时自动切换离线导航",
        keywords=["断网", "离线", "导航", "本地"],
        metadata={"topic": "fallback"},
    ),
]


PROFILE_DOCUMENTS = [
    RetrievalDocument(
        doc_id="profile_user_001",
        text="user_001：温度24℃，座椅加热自动开启，路线偏好高速",
        keywords=["user_001", "温度24", "座椅加热", "路线偏好高速", "高速", "导航"],
        metadata={
            "user_id": "user_001",
            "temperature": "24℃",
            "seat_heat": "自动开启",
            "route_preference": "高速",
        },
    ),
    RetrievalDocument(
        doc_id="profile_user_002",
        text="user_002：温度22℃，音乐音量30%，充电提醒20%",
        keywords=["user_002", "温度22", "音乐", "音量30", "充电提醒20", "电量", "充电"],
        metadata={
            "user_id": "user_002",
            "temperature": "22℃",
            "music_volume": "30%",
            "charge_reminder": "20%",
        },
    ),
]
