from dataclasses import dataclass

from core.constants import CommandType, NetworkStatus, SafetyLevel


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    reason: str


class SafetyPolicy:
    def evaluate(
        self,
        command_type: CommandType,
        safety: SafetyLevel,
        network: NetworkStatus,
        content: str,
    ) -> SafetyDecision:
        if safety == SafetyLevel.DANGEROUS:
            return SafetyDecision(False, "危险指令，已拦截！")

        if command_type == CommandType.UNKNOWN:
            return SafetyDecision(False, "未知指令，未进入执行链路")

        return SafetyDecision(True, "安全策略通过")
