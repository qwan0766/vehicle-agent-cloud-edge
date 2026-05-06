from agents.vehicle.car_control_agent import CarControlAgent
from agents.vehicle.nav_agent import NavAgent
from core.constants import CommandType


class CabinVehicleControlAgent:
    role_name = "座舱/车控 Agent"

    def __init__(self, car_control_agent=None, nav_agent=None):
        self.car_control_agent = car_control_agent or CarControlAgent()
        self.nav_agent = nav_agent or NavAgent()

    def execute(self, command_type: CommandType, command: str, local_context=None) -> str:
        if command_type == CommandType.CAR_CONTROL:
            return self.car_control_agent.execute(command)
        if command_type == CommandType.NAVIGATION:
            return self.nav_agent.start(command)
        if command_type == CommandType.CHARGE_PLAN:
            return "断网模式：根据本地知识库建议前往最近换电站"
        if command_type == CommandType.PERSONALIZE:
            return self._local_personalize_response(local_context)
        return "断网模式：当前指令无法本地执行"

    def _local_personalize_response(self, local_context) -> str:
        context = local_context or {}
        recent_count = len(context.get("recent_turns", []))
        summary = context.get("summary") or "暂无压缩摘要"
        preferences = context.get("preference_state") or {}
        preference_text = (
            "、".join(f"{key}={value}" for key, value in preferences.items())
            if preferences
            else "暂无动态偏好"
        )
        return (
            "断网模式：使用本地用户画像与本地意图 Agent 上下文。\n"
            f"- 历史摘要：{summary}\n"
            f"- 最近交互：{recent_count} 条\n"
            f"- 动态偏好：{preference_text}"
        )
