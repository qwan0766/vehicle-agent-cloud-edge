from dataclasses import dataclass
import re

from core.constants import CommandType, ExecutionStatus, NetworkStatus, RoadType, SafetyLevel


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str
    status: ExecutionStatus = None


class SafetyPolicy:
    def evaluate(
        self,
        command_type: CommandType,
        safety: SafetyLevel,
        network: NetworkStatus,
        content: str,
        vehicle_state: dict = None,
    ) -> SafetyDecision:
        if safety == SafetyLevel.DANGEROUS:
            contextual = _evaluate_contextual_motion_request(content, vehicle_state)
            if contextual:
                return contextual
            return SafetyDecision(
                False,
                "危险指令，已拦截！涉及动力、制动、转向或安全辅助关闭，系统不会直接执行。",
                ExecutionStatus.BLOCKED,
            )

        if command_type == CommandType.UNKNOWN:
            return SafetyDecision(False, "未知指令，未进入执行链路", ExecutionStatus.BLOCKED)

        return SafetyDecision(True, "安全策略通过", ExecutionStatus.EXECUTED)


def _evaluate_contextual_motion_request(content: str, vehicle_state: dict):
    target_speed = _extract_target_speed(content)
    if target_speed is None:
        return None
    if not vehicle_state:
        return None

    road_type = str(vehicle_state.get("road_type", RoadType.UNKNOWN.value))
    speed_limit = int(vehicle_state.get("speed_limit_kmh") or 0)
    if road_type != RoadType.HIGHWAY.value:
        return SafetyDecision(
            False,
            "当前不是高速场景，车速调整请求已拦截。请由驾驶员根据道路限速自行操作。",
            ExecutionStatus.BLOCKED,
        )
    if speed_limit <= 0 or target_speed > speed_limit:
        return SafetyDecision(
            False,
            f"目标速度{target_speed}km/h超过当前限速{speed_limit}km/h，已拦截。",
            ExecutionStatus.BLOCKED,
        )
    return SafetyDecision(
        True,
        (
            f"当前为高速场景，限速{speed_limit}km/h。系统不会直接控制动力，"
            f"仅建议将巡航目标设为{target_speed}km/h，请驾驶员确认。"
        ),
        ExecutionStatus.NEEDS_DRIVER_CONFIRMATION,
    )


def _extract_target_speed(content: str):
    normalized = (content or "").replace(" ", "")
    if not any(marker in normalized for marker in ("加速到", "提速到", "巡航到", "速度到")):
        return None
    match = re.search(r"(\d{2,3})\s*(?:km/h|公里|码)?", normalized, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))
