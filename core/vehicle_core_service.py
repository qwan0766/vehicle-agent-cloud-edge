from dataclasses import dataclass

from agents.orchestrator.global_dispatch_agent import GlobalDispatchAgent
from agents.vehicle.cabin_vehicle_control_agent import CabinVehicleControlAgent
from agents.vehicle.data_upload_agent import DataUploadAgent
from agents.vehicle.energy_policy_agent import EnergyPolicyAgent
from agents.vehicle.global_safety_dispatch_agent import GlobalSafetyDispatchAgent
from agents.vehicle.input_rewrite_agent import InputRewriteAgent, normalize_rewrite_result
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
from memory.pending_action_store import PendingActionStore
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
    pending_action: dict = None
    input_rewrite: dict = None


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
        pending_action_store=None,
        destination_confidence_agent=None,
        vehicle_state=None,
        state_monitor_agent=None,
        energy_policy_agent=None,
        input_rewrite_agent=None,
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
        self.pending_action_store = pending_action_store or PendingActionStore()
        self.destination_confidence_agent = (
            destination_confidence_agent or DestinationConfidenceAgent()
        )
        self.vehicle_state = vehicle_state or DEFAULT_VEHICLE_STATE
        self.state_monitor_agent = state_monitor_agent or VehicleStateMonitorAgent()
        self.energy_policy_agent = energy_policy_agent or EnergyPolicyAgent()
        self.input_rewrite_agent = input_rewrite_agent or InputRewriteAgent(
            context_manager=self.context_manager
        )

    def run(
        self,
        user_input: str,
        user_id: str = "user_001",
        network: NetworkStatus = NetworkStatus.ONLINE,
    ) -> ExecutionResult:
        raw_input = user_input
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

        rewrite_result = self._rewrite_input(
            raw_input=raw_input,
            current_input=user_input,
            user_id=user_id,
            network=network,
        )
        user_input = rewrite_result.rewritten_input or user_input
        input_rewrite = rewrite_result.to_dict()

        command_type = (
            rewrite_result.intent_hint
            if rewrite_result.intent_hint != CommandType.UNKNOWN
            else self.intent_agent.recognize(
                user_input,
                user_id=user_id,
                preference_state=self._local_preference_state(user_id),
                vehicle_state=self._vehicle_state_payload(network),
            )
        )
        raw_safety = self.safety_agent.check(raw_input)
        rewritten_safety = self.safety_agent.check(user_input)
        safety = (
            raw_safety
            if raw_safety.value == "DANGEROUS"
            else rewritten_safety
        )
        if rewrite_result.needs_clarification:
            msg = Message.create(
                user_id=user_id,
                command_type=command_type,
                safety=safety,
                content=user_input,
                network=network,
            )
            clarification = {
                "type": "input_rewrite",
                "reason": "input_rewrite_clarification",
                "question": rewrite_result.reason or "我需要你补充一下指令细节。",
                "raw_input": raw_input,
                "rewritten_input": user_input,
                "slots": rewrite_result.slots or {},
            }
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.NEEDS_CLARIFICATION,
                    output=clarification["question"],
                    message=msg,
                    clarification=clarification,
                    input_rewrite=input_rewrite,
                )
            )
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
            content=self._safety_evaluation_content(raw_input, user_input),
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
                    input_rewrite=input_rewrite,
                )
            )
        if safety_decision.status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION:
            pending_action = self._create_pending_action(
                "driver_confirmation",
                user_id,
                user_input,
                command_type,
                network,
                safety_decision.reason,
                {"vehicle_state": self._vehicle_state_payload(network)},
            )
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.NEEDS_DRIVER_CONFIRMATION,
                    output=safety_decision.reason,
                    message=msg,
                    pending_action=pending_action,
                    input_rewrite=input_rewrite,
                )
            )

        energy_decision = self.energy_policy_agent.evaluate(
            command_type=command_type,
            content=user_input,
            vehicle_state=self.vehicle_state,
        )
        if not energy_decision.allowed:
            pending_action = None
            if energy_decision.status == ExecutionStatus.NEEDS_CHARGE_CONFIRMATION:
                pending_action = self._create_pending_action(
                    "charge_confirmation",
                    user_id,
                    user_input,
                    command_type,
                    network,
                    energy_decision.reason,
                    {"vehicle_state": self._vehicle_state_payload(network)},
                )
            return self._complete_result(
                ExecutionResult(
                    status=energy_decision.status,
                    output=energy_decision.reason,
                    message=msg,
                    pending_action=pending_action,
                    input_rewrite=input_rewrite,
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
            pending_action = self._create_pending_action(
                "destination_clarification",
                user_id,
                user_input,
                command_type,
                network,
                clarification["question"],
                {"clarification": clarification},
            )
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.NEEDS_CLARIFICATION,
                    output=clarification["question"],
                    message=msg,
                    trace=self._destination_confidence_trace(),
                    clarification=clarification,
                    pending_action=pending_action,
                    input_rewrite=input_rewrite,
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
            output = self._append_energy_advisory(output, energy_decision)
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.FALLBACK,
                    output=output,
                    message=msg,
                    local_context=local_context,
                    input_rewrite=input_rewrite,
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
            pending_action = self._create_pending_action(
                "destination_clarification",
                user_id,
                user_input,
                command_type,
                network,
                clarification["question"],
                {"clarification": clarification},
            )
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.NEEDS_CLARIFICATION,
                    output=clarification["question"],
                    message=msg,
                    clarification=clarification,
                    trace=self._destination_confidence_trace(),
                    graph=self._cloud_graph_snapshot(),
                    pending_action=pending_action,
                    input_rewrite=input_rewrite,
                )
            )
        cloud_safety_result = self._review_cloud_output(
            output,
            msg,
            command_type,
            user_input,
            user_id,
            network,
        )
        if cloud_safety_result:
            return self._with_input_rewrite(cloud_safety_result, input_rewrite)
        output = self._append_energy_advisory(output, energy_decision)
        return self._complete_result(
            ExecutionResult(
                status=ExecutionStatus.EXECUTED,
                output=output,
                message=msg,
                trace=self.cloud_agent.get_last_trace(),
                graph=self._cloud_graph_snapshot(),
                input_rewrite=input_rewrite,
            )
        )

    def confirm_pending_action(
        self,
        action_id: str,
        user_id: str = "user_001",
        confirmed: bool = True,
        selection: dict = None,
    ) -> ExecutionResult:
        action = self.pending_action_store.get(action_id)
        if not action or action.get("user_id") != user_id:
            raise ValueError("Pending action not found or expired")

        self.pending_action_store.clear(action_id)
        self.pending_clarification_store.clear(user_id, action.get("session_id") or DEFAULT_SESSION_ID)

        command_type = CommandType(action.get("command_type"))
        network = NetworkStatus(action.get("network"))
        content = action.get("content") or ""
        if not confirmed:
            msg = Message.create(
                user_id=user_id,
                command_type=command_type,
                safety=self.safety_agent.check(content),
                content=content,
                network=network,
            )
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.BLOCKED,
                    output="已取消待确认操作，系统不会继续执行该指令。",
                    message=msg,
                )
            )

        action_type = action.get("type")
        if action_type == "destination_clarification":
            confirmed_content = self._confirmed_destination_content(action, selection or {})
            return self.run(confirmed_content, user_id=user_id, network=network)

        if action_type == "driver_confirmation":
            msg = Message.create(
                user_id=user_id,
                command_type=command_type,
                safety=self.safety_agent.check(content),
                content=content,
                network=network,
            )
            output = f"驾驶员确认后执行：{content}"
            if command_type == CommandType.CAR_CONTROL:
                output = f"驾驶员确认后执行。\n{self.control_agent.execute(command_type, content)}"
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.EXECUTED,
                    output=output,
                    message=msg,
                )
            )

        if action_type == "charge_confirmation":
            return self._execute_after_charge_confirmation(content, user_id, command_type, network)

        raise ValueError(f"Unsupported pending action type: {action_type}")

    def _execute_after_charge_confirmation(
        self,
        content: str,
        user_id: str,
        command_type: CommandType,
        network: NetworkStatus,
    ) -> ExecutionResult:
        safety = self.safety_agent.check(content)
        msg = Message.create(
            user_id=user_id,
            command_type=command_type,
            safety=safety,
            content=content,
            network=network,
        )
        if network == NetworkStatus.OFFLINE:
            local_context = self.intent_agent.build_local_llm_context(
                user_id=user_id,
                preference_state=self._local_preference_state(user_id),
                current_input=content,
                vehicle_state=self._vehicle_state_payload(network),
            )
            output = self._run_local(command_type, content, local_context)
            return self._complete_result(
                ExecutionResult(
                    status=ExecutionStatus.FALLBACK,
                    output=f"已确认低电量补能风险。\n{output}",
                    message=msg,
                    local_context=local_context,
                )
            )

        output = self.cloud_agent.dispatch(msg)
        cloud_safety_result = self._review_cloud_output(
            output,
            msg,
            command_type,
            content,
            user_id,
            network,
        )
        if cloud_safety_result:
            return cloud_safety_result
        return self._complete_result(
            ExecutionResult(
                status=ExecutionStatus.EXECUTED,
                output=f"已确认低电量补能风险。\n{output}",
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

    def _append_energy_advisory(self, output: str, energy_decision) -> str:
        advisory = getattr(energy_decision, "advisory", "")
        if not advisory:
            return output
        return f"{output}\n\n{advisory}"

    def _rewrite_input(
        self,
        raw_input: str,
        current_input: str,
        user_id: str,
        network: NetworkStatus,
    ):
        rewrite = self.input_rewrite_agent.rewrite(
            current_input,
            user_id=user_id,
            preference_state=self._local_preference_state(user_id),
            vehicle_state=self._vehicle_state_payload(network),
        )
        result = normalize_rewrite_result(rewrite, raw_input=current_input)
        if raw_input != current_input:
            payload = result.to_dict()
            payload["raw_input"] = raw_input
            payload["post_clarification_input"] = current_input
            return normalize_rewrite_result(payload, raw_input=raw_input)
        return result

    def _safety_evaluation_content(self, raw_input: str, rewritten_input: str) -> str:
        if raw_input == rewritten_input:
            return rewritten_input
        return f"原始输入：{raw_input}\n重写输入：{rewritten_input}"

    def _with_input_rewrite(self, result: ExecutionResult, input_rewrite: dict):
        return ExecutionResult(
            status=result.status,
            output=result.output,
            message=result.message,
            feedback=result.feedback,
            trace=result.trace,
            local_context=result.local_context,
            graph=result.graph,
            clarification=result.clarification,
            pending_action=result.pending_action,
            input_rewrite=input_rewrite,
        )

    def _review_cloud_output(
        self,
        output: str,
        msg: Message,
        command_type: CommandType,
        content: str,
        user_id: str,
        network: NetworkStatus,
    ):
        review = getattr(self.safety_agent, "verify_cloud_result_decision", None)
        if callable(review):
            decision = review(
                output,
                command_type=command_type,
                vehicle_state=self._vehicle_state_payload(network),
            )
            if not decision.allowed:
                return self._complete_result(
                    ExecutionResult(
                        status=ExecutionStatus.BLOCKED,
                        output=decision.reason,
                        message=msg,
                        trace=self.cloud_agent.get_last_trace(),
                        graph=self._cloud_graph_snapshot(),
                    )
                )
            if decision.status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION:
                pending_action = self._create_pending_action(
                    "driver_confirmation",
                    user_id,
                    content,
                    command_type,
                    network,
                    decision.reason,
                    {
                        "vehicle_state": self._vehicle_state_payload(network),
                        "cloud_output": output,
                        "safety_review_source": decision.source,
                    },
                )
                return self._complete_result(
                    ExecutionResult(
                        status=ExecutionStatus.NEEDS_DRIVER_CONFIRMATION,
                        output=decision.reason,
                        message=msg,
                        trace=self.cloud_agent.get_last_trace(),
                        graph=self._cloud_graph_snapshot(),
                        pending_action=pending_action,
                    )
                )
            return None

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
        return None

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
                pending_action=result.pending_action,
                input_rewrite=result.input_rewrite,
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
            pending_action=result.pending_action,
            input_rewrite=result.input_rewrite,
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

    def _create_pending_action(
        self,
        action_type: str,
        user_id: str,
        content: str,
        command_type: CommandType,
        network: NetworkStatus,
        reason: str,
        payload: dict = None,
    ) -> dict:
        return self.pending_action_store.create(
            action_type=action_type,
            user_id=user_id,
            session_id=DEFAULT_SESSION_ID,
            content=content,
            command_type=command_type.value,
            network=network.value,
            reason=reason,
            payload=payload or {},
        )

    def _confirmed_destination_content(self, action: dict, selection: dict) -> str:
        payload = action.get("payload") or {}
        clarification = payload.get("clarification") or {}
        gps = (selection.get("gps") or "").strip()
        if gps:
            return f"导航去{gps}"
        selected = (
            selection.get("content")
            or selection.get("name")
            or selection.get("query")
            or ""
        ).strip()
        if not selected:
            selected = clarification.get("query", "")
        if selected.startswith(("导航去", "导航到", "去", "到")):
            return selected
        if is_destination_refinement(selected, clarification):
            return reconstruct_destination_command(selected, clarification)
        return f"导航去{selected}"
