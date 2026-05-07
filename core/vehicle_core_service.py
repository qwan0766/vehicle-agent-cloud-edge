from dataclasses import dataclass

from agents.orchestrator.global_dispatch_agent import GlobalDispatchAgent
from agents.vehicle.cabin_vehicle_control_agent import CabinVehicleControlAgent
from agents.vehicle.data_upload_agent import DataUploadAgent
from agents.vehicle.global_safety_dispatch_agent import GlobalSafetyDispatchAgent
from agents.vehicle.local_intent_agent import LocalIntentAgent
from agents.cloud.destination_confidence_agent import DestinationConfidenceAgent
from agents.vehicle.vehicle_state_monitor_agent import VehicleStateMonitorAgent
from core.clarification import (
    build_destination_clarification,
    is_destination_refinement,
    reconstruct_destination_command,
)
from core.constants import CommandType, ExecutionStatus, NetworkStatus
from core.message import Message
from data.vehicle_state import DEFAULT_VEHICLE_STATE
from memory.local_agent_context_manager import DEFAULT_SESSION_ID, LocalAgentContextManager
from memory.pending_clarification_store import PendingClarificationStore
from providers.destination_resolver import (
    DestinationClarificationRequired,
    resolve_destination_detail,
)
from providers.factory import create_destination_candidate_provider, create_geocode_provider


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    output: str
    message: Message
    feedback: dict = None
    trace: list = None
    local_context: dict = None
    graph: dict = None
    clarification: dict = None


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
        pending_clarification_store=None,
        destination_confidence_agent=None,
        vehicle_state=None,
        state_monitor_agent=None,
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
        self.pending_clarification_store = (
            pending_clarification_store or PendingClarificationStore()
        )
        self.destination_confidence_agent = (
            destination_confidence_agent or DestinationConfidenceAgent()
        )
        self.vehicle_state = vehicle_state or DEFAULT_VEHICLE_STATE
        self.state_monitor_agent = state_monitor_agent or VehicleStateMonitorAgent()

    def run(
        self,
        user_input: str,
        user_id: str = "user_001",
        network: NetworkStatus = NetworkStatus.ONLINE,
    ) -> ExecutionResult:
        pending_clarification = self.pending_clarification_store.get(
            user_id,
            DEFAULT_SESSION_ID,
        )
        if pending_clarification:
            if is_destination_refinement(user_input, pending_clarification):
                user_input = reconstruct_destination_command(
                    user_input,
                    pending_clarification,
                )
            self.pending_clarification_store.clear(user_id, DEFAULT_SESSION_ID)

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
            vehicle_state=self._vehicle_state_payload(network),
        )
        if not safety_decision.allowed:
            explain_blocked = getattr(
                self.safety_agent,
                "explain_blocked_command",
                None,
            )
            output = (
                explain_blocked(
                    content=user_input,
                    command_type=command_type,
                    policy_reason=safety_decision.reason,
                )
                if callable(explain_blocked)
                else safety_decision.reason
            )
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.BLOCKED,
                    output=output,
                    message=msg,
                )
            )
        if safety_decision.status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION:
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.NEEDS_DRIVER_CONFIRMATION,
                    output=safety_decision.reason,
                    message=msg,
                )
            )

        clarification = self._destination_clarification(
            user_input,
            command_type,
            network,
            user_id,
        )
        if clarification:
            self.pending_clarification_store.save(
                user_id,
                DEFAULT_SESSION_ID,
                clarification,
            )
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.NEEDS_CLARIFICATION,
                    output=clarification["question"],
                    message=msg,
                    trace=self._destination_confidence_trace(),
                    clarification=clarification,
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

        try:
            output = self.cloud_agent.dispatch(msg)
        except DestinationClarificationRequired as exc:
            clarification = build_destination_clarification(
                exc,
                original_content=user_input,
            )
            self.pending_clarification_store.save(
                user_id,
                DEFAULT_SESSION_ID,
                clarification,
            )
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.NEEDS_CLARIFICATION,
                    output=clarification["question"],
                    message=msg,
                    clarification=clarification,
                    trace=self._destination_confidence_trace(),
                    graph=self._cloud_graph_snapshot(),
                )
            )
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

    def _destination_clarification(
        self,
        user_input: str,
        command_type: CommandType,
        network: NetworkStatus,
        user_id: str,
    ):
        if command_type not in {CommandType.NAVIGATION, CommandType.CHARGE_PLAN}:
            return None
        try:
            resolve_destination_detail(user_input, geocoder=None)
        except DestinationClarificationRequired as exc:
            return build_destination_clarification(exc, original_content=user_input)
        except ValueError:
            if command_type != CommandType.NAVIGATION:
                return None
        else:
            return None

        try:
            self.destination_confidence_agent.ensure_executable(
                user_input,
                candidate_provider=(
                    create_destination_candidate_provider()
                    if network == NetworkStatus.ONLINE
                    else None
                ),
                geocoder=create_geocode_provider() if network == NetworkStatus.ONLINE else None,
                frequent_destinations=self._frequent_navigation_destinations(user_id),
            )
        except DestinationClarificationRequired as exc:
            return build_destination_clarification(exc, original_content=user_input)
        return None

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
                clarification=result.clarification,
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
            clarification=result.clarification,
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
            "speed_kmh": self.vehicle_state.speed_kmh,
            "battery_percent": self.vehicle_state.battery_percent,
            "network": network.value,
            "gps": self.vehicle_state.gps,
            "road_type": self.vehicle_state.road_type.value,
            "speed_limit_kmh": self.vehicle_state.speed_limit_kmh,
            "driver_assist_mode": self.vehicle_state.driver_assist_mode.value,
            "vehicle_ready": self.vehicle_state.vehicle_ready,
            "lane_confidence": self.vehicle_state.lane_confidence,
        }

    def detect_state_events(self):
        return self.state_monitor_agent.detect_events(self.vehicle_state)

    def _frequent_navigation_destinations(self, user_id: str):
        if not self.feedback_service:
            return set()
        getter = getattr(
            self.feedback_service,
            "get_frequent_navigation_destinations",
            None,
        )
        if not callable(getter):
            return set()
        return getter(user_id)

    def _destination_confidence_trace(self):
        trace_getter = getattr(self.destination_confidence_agent, "get_last_trace", None)
        if not callable(trace_getter):
            return []
        return trace_getter()
