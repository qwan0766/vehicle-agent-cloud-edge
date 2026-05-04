from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.vehicle_core_service import VehicleCoreService
from data.vehicle_state import DEFAULT_VEHICLE_STATE
from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from agents.vehicle.local_intent_agent import LocalIntentAgent
from feedback.feedback_service import FeedbackService


SCENARIOS = [
    {"label": "导航去蔚来中心", "content": "导航去蔚来中心", "network": "ONLINE"},
    {"label": "打开座椅加热", "content": "打开座椅加热", "network": "OFFLINE"},
    {"label": "电量低", "content": "电量低", "network": "ONLINE"},
    {"label": "我的偏好", "content": "我的偏好", "network": "ONLINE"},
    {"label": "加速到100km/h", "content": "加速到100km/h", "network": "ONLINE"},
]


def get_initial_payload():
    return {
        "vehicle_state": _vehicle_state_payload(NetworkStatus.ONLINE),
        "scenarios": SCENARIOS,
    }


def run_command(content: str, user_id: str = "user_001", network: str = "ONLINE"):
    network_status = _parse_network(network)
    service = VehicleCoreService(feedback_service=FeedbackService())
    result = service.run(content, user_id=user_id, network=network_status)

    return {
        "vehicle_state": _vehicle_state_payload(network_status),
        "request": {
            "request_id": result.message.request_id,
            "user_id": result.message.user_id,
            "command_type": result.message.command_type.value,
            "safety": result.message.safety.value,
            "content": result.message.content,
            "network": result.message.network.value,
        },
        "result": {
            "status": result.status.value,
            "output": result.output,
        },
        "feedback": result.feedback or {},
        "rag_context": _rag_context(
            result.message.content,
            result.message.user_id,
            result.message.command_type,
            result.message.network,
        ),
        "agent_trace": _agent_trace(result.message.command_type, result.message.safety, result.status),
    }


def _parse_network(network: str) -> NetworkStatus:
    normalized = (network or "ONLINE").upper()
    if normalized == NetworkStatus.OFFLINE.value:
        return NetworkStatus.OFFLINE
    return NetworkStatus.ONLINE


def _vehicle_state_payload(network: NetworkStatus):
    return {
        "speed_kmh": DEFAULT_VEHICLE_STATE.speed_kmh,
        "battery_percent": DEFAULT_VEHICLE_STATE.battery_percent,
        "network": network.value,
        "gps": DEFAULT_VEHICLE_STATE.gps,
        "safety_state": "正常",
    }


def _agent_trace(command_type: CommandType, safety: SafetyLevel, status: ExecutionStatus):
    trace = ["LocalIntentAgent", "SafetyAgent"]

    if safety == SafetyLevel.DANGEROUS or status == ExecutionStatus.BLOCKED:
        trace.append("SafetyBlock")
        return trace

    if status == ExecutionStatus.FALLBACK:
        if command_type == CommandType.NAVIGATION:
            trace.append("NavAgent")
        elif command_type == CommandType.CAR_CONTROL:
            trace.append("CarControlAgent")
        else:
            trace.append("LocalFallback")
        return trace

    trace.extend(
        [
            "CloudScheduleAgent",
            "CloudUserProfileAgent",
            "CloudEcologyAgent",
            "CloudRoutePlanAgent",
        ]
    )
    return trace


def _rag_context(content: str, user_id: str, command_type: CommandType, network: NetworkStatus):
    context = []

    intent_agent = LocalIntentAgent()
    for result in intent_agent.retrieve_context(content):
        context.append(_context_payload("本地意图识别", result))

    if network == NetworkStatus.ONLINE and command_type in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
        CommandType.PERSONALIZE,
    }:
        profile_agent = CloudUserProfileAgent()
        for result in profile_agent.retrieve_context(user_id, content):
            context.append(_context_payload("用户画像召回", result))

        route_agent = CloudRoutePlanAgent()
        for result in route_agent.retrieve_context(content):
            context.append(_context_payload("云端路线规划", result))

    return context


def _context_payload(stage: str, result):
    return {
        "stage": stage,
        "doc_id": result.document.doc_id,
        "text": result.document.text,
        "score": result.score,
        "matched_keywords": result.matched_keywords,
    }
