from dataclasses import dataclass

from agents.cloud.cloud_schedule_agent import CloudScheduleAgent
from agents.vehicle.car_control_agent import CarControlAgent
from agents.vehicle.local_intent_agent import LocalIntentAgent
from agents.vehicle.nav_agent import NavAgent
from agents.vehicle.safety_agent import SafetyAgent
from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.message import Message


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    output: str
    message: Message
    feedback: dict = None


class VehicleCoreService:
    def __init__(self, feedback_service=None):
        self.safety_agent = SafetyAgent()
        self.intent_agent = LocalIntentAgent()
        self.car_control_agent = CarControlAgent()
        self.nav_agent = NavAgent()
        self.cloud_agent = CloudScheduleAgent()
        self.feedback_service = feedback_service

    def run(
        self,
        user_input: str,
        user_id: str = "user_001",
        network: NetworkStatus = NetworkStatus.ONLINE,
    ) -> ExecutionResult:
        command_type = self.intent_agent.recognize(user_input)
        safety = self.safety_agent.check(user_input)
        msg = Message.create(
            user_id=user_id,
            command_type=command_type,
            safety=safety,
            content=user_input,
            network=network,
        )

        if safety == SafetyLevel.DANGEROUS:
            return self._with_feedback(
                ExecutionResult(
                    status=ExecutionStatus.BLOCKED,
                    output="危险指令，已拦截！",
                    message=msg,
                )
            )

        if network == NetworkStatus.OFFLINE:
            output = self._run_local(command_type, user_input)
            return self._with_feedback(
                ExecutionResult(
                    status=ExecutionStatus.FALLBACK,
                    output=output,
                    message=msg,
                )
            )

        output = self.cloud_agent.dispatch(msg)
        return self._with_feedback(
            ExecutionResult(
                status=ExecutionStatus.EXECUTED,
                output=output,
                message=msg,
            )
        )

    def _run_local(self, command_type: CommandType, user_input: str) -> str:
        if command_type == CommandType.CAR_CONTROL:
            return self.car_control_agent.execute(user_input)
        if command_type == CommandType.NAVIGATION:
            return self.nav_agent.start(user_input)
        if command_type == CommandType.CHARGE_PLAN:
            return "断网模式：根据本地知识库建议前往最近换电站"
        if command_type == CommandType.PERSONALIZE:
            return "断网模式：使用本地默认偏好，温度24℃"
        return "断网模式：当前指令无法本地执行"

    def _with_feedback(self, result: ExecutionResult) -> ExecutionResult:
        if not self.feedback_service:
            return result
        feedback = self.feedback_service.record(result)
        return ExecutionResult(
            status=result.status,
            output=result.output,
            message=result.message,
            feedback=feedback,
        )
