from dataclasses import dataclass

from core.constants import CommandType, ExecutionStatus


@dataclass(frozen=True)
class EnergyDecision:
    allowed: bool
    status: ExecutionStatus
    reason: str = ""
    advisory: str = ""


class EnergyPolicyAgent:
    role_name = "能源策略 Agent"

    def __init__(
        self,
        low_battery_threshold: int = 20,
        critical_battery_threshold: int = 10,
        comfort_block_threshold: int = 5,
    ):
        self.low_battery_threshold = low_battery_threshold
        self.critical_battery_threshold = critical_battery_threshold
        self.comfort_block_threshold = comfort_block_threshold

    def evaluate(self, command_type: CommandType, content: str, vehicle_state) -> EnergyDecision:
        battery = int(getattr(vehicle_state, "battery_percent", 0))

        if battery <= self.comfort_block_threshold and _is_comfort_power_request(content):
            return EnergyDecision(
                allowed=False,
                status=ExecutionStatus.BLOCKED,
                reason=(
                    f"当前电量{battery}%，属于低电量保护场景。"
                    "座椅加热等舒适性耗电功能已暂缓执行，建议优先补能。"
                ),
            )

        if command_type == CommandType.NAVIGATION and battery <= self.critical_battery_threshold:
            return EnergyDecision(
                allowed=False,
                status=ExecutionStatus.NEEDS_CHARGE_CONFIRMATION,
                reason=(
                    f"电量严重不足：当前电量{battery}%。"
                    "系统建议先确认补能规划，再继续导航。"
                ),
            )

        if command_type == CommandType.NAVIGATION and battery <= self.low_battery_threshold:
            return EnergyDecision(
                allowed=True,
                status=ExecutionStatus.EXECUTED,
                advisory=(
                    f"能源提示：当前电量{battery}%，建议规划补能点，"
                    "并在路线中关注可用充电站或换电站。"
                ),
            )

        return EnergyDecision(allowed=True, status=ExecutionStatus.EXECUTED)


def _is_comfort_power_request(content: str) -> bool:
    normalized = content or ""
    return any(keyword in normalized for keyword in ("座椅加热", "方向盘加热", "空调增强", "极速制热"))
