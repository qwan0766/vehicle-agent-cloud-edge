from core.constants import CommandType


INTENT_KNOWLEDGE = {
    "导航去蔚来中心": CommandType.NAVIGATION,
    "我要回家": CommandType.NAVIGATION,
    "打开座椅加热": CommandType.CAR_CONTROL,
    "温度调到24度": CommandType.CAR_CONTROL,
    "电量低": CommandType.CHARGE_PLAN,
    "我的偏好": CommandType.PERSONALIZE,
}

ROUTE_KNOWLEDGE = [
    "电量低于20%建议前往换电站",
    "长途优先高速路线",
    "车内舒适温度22~25℃",
    "换电站约3分钟完成换电",
    "断网时自动切换离线导航",
]

DANGEROUS_KEYWORDS = [
    "动力",
    "制动",
    "转向",
    "加速",
    "刹车",
    "AEB",
    "自动紧急制动",
    "方向盘",
    "接管",
]

ECOLOGY_DATA = {
    "weather": "天气晴",
    "swap_station": "换电站空闲",
}
