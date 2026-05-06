from dataclasses import dataclass

from agents.orchestrator.global_dispatch_agent import GlobalDispatchAgent
from agents.vehicle.cabin_vehicle_control_agent import CabinVehicleControlAgent
from agents.vehicle.data_upload_agent import DataUploadAgent
from agents.vehicle.global_safety_dispatch_agent import GlobalSafetyDispatchAgent
from agents.vehicle.local_intent_agent import LocalIntentAgent
from core.constants import CommandType, ExecutionStatus, NetworkStatus
from core.message import Message
from data.vehicle_state import DEFAULT_VEHICLE_STATE
from memory.local_agent_context_manager import LocalAgentContextManager


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    output: str
    message: Message
    feedback: dict = None
    trace: list = None
    local_context: dict = None
    graph: dict = None


class VehicleCoreService:
    def __init__(
        self,
        feedback_service=None,
        cloud_agent=None,
        context_manager=None,
        intent_agent=None,
        safety_agent=None,
        control_agent=None,
        data_upload_agent=None,
    ):
        self.context_manager = context_manager or LocalAgentContextManager()
        self.intent_agent = intent_agent or LocalIntentAgent(
            context_manager=self.context_manager
        )
        self.safety_agent = safety_agent or GlobalSafetyDispatchAgent()
        self.control_agent = control_agent or CabinVehicleControlAgent()
        self.car_control_agent = self.control_agent.car_control_agent
        self.nav_agent = self.control_agent.nav_agent
        self.cloud_agent = cloud_agent or GlobalDispatchAgent()
        self.feedback_service = feedback_service
        self.data_upload_agent = data_upload_agent or DataUploadAgent(feedback_service)

    def run(
        self,
        user_input: str,
        user_id: str = "user_001",
        network: NetworkStatus = NetworkStatus.ONLINE,
    ) -> ExecutionResult:
        command_type = self.intent_agent.recognize(
            user_input,
            user_id=user_id,
            preference_state=self._local_preference_state(user_id),
            vehicle_state=self._vehicle_state_payload(network),
        )
        safety = self.safety_agent.check(user_input)
        msg = Message.create(
            user_id=user_id,
            command_type=command_type,
            safety=safety,
            content=user_input,
            network=network,
        )

        safety_decision = self.safety_agent.evaluate(
            command_type=command_type,
            safety=safety,
            network=network,
            content=user_input,
        )
        if not safety_decision.allowed:
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.BLOCKED,
                    output=safety_decision.reason,
                    message=msg,
                )
            )

        if network == NetworkStatus.OFFLINE:
            local_context = self.intent_agent.build_local_llm_context(
                user_id=user_id,
                preference_state=self._local_preference_state(user_id),
                current_input=user_input,
                vehicle_state=self._vehicle_state_payload(network),
            )
            output = self._run_local(command_type, user_input, local_context)
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.FALLBACK,
                    output=output,
                    message=msg,
                    local_context=local_context,
                )
            )

        output = self.cloud_agent.dispatch(msg)
        allowed, reason = self.safety_agent.verify_cloud_result(output)
        if not allowed:
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.BLOCKED,
                    output=reason,
                    message=msg,
                    trace=self.cloud_agent.get_last_trace(),
                    graph=self._cloud_graph_snapshot(),
                )
            )
        return self._complete_result(
            ExecutionResult(
                status=ExecutionStatus.EXECUTED,
                output=output,
                message=msg,
                trace=self.cloud_agent.get_last_trace(),
                graph=self._cloud_graph_snapshot(),
            )
        )

    def _run_local(
        self,
        command_type: CommandType,
        user_input: str,
        local_context=None,
    ) -> str:
        return self.control_agent.execute(command_type, user_input, local_context)

    def _complete_result(self, result: ExecutionResult) -> ExecutionResult:
        context_snapshot = None
        if self.intent_agent:
            context_snapshot = self.intent_agent.record_result(result)
            result = ExecutionResult(
                status=result.status,
                output=result.output,
                message=result.message,
                feedback=result.feedback,
                trace=result.trace,
                local_context=context_snapshot,
                graph=result.graph,
            )
        return self._with_feedback(result)

    def _with_feedback(self, result: ExecutionResult) -> ExecutionResult:
        feedback = self.data_upload_agent.record(result)
        if not feedback:
            return result
        return ExecutionResult(
            status=result.status,
            output=result.output,
            message=result.message,
            feedback=feedback,
            trace=result.trace,
            local_context=result.local_context,
            graph=result.graph,
        )

    def _cloud_graph_snapshot(self):
        get_last_graph = getattr(self.cloud_agent, "get_last_graph", None)
        if not callable(get_last_graph):
            return {}
        return get_last_graph()

    def _local_preference_state(self, user_id: str):
        if not self.feedback_service:
            return {}
        preference_store = getattr(self.feedback_service, "preference_store", None)
        if not preference_store:
            return {}
        return preference_store.get_user_state(user_id)

    def _vehicle_state_payload(self, network: NetworkStatus):
        return {
            "speed_kmh": DEFAULT_VEHICLE_STATE.speed_kmh,
            "battery_percent": DEFAULT_VEHICLE_STATE.battery_percent,
            "network": network.value,
            "gps": DEFAULT_VEHICLE_STATE.gps,
        }
