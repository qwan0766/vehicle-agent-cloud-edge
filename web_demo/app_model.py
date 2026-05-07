from pathlib import Path

from agents.cloud.global_trip_planning_agent import GlobalTripPlanningAgent
from agents.cloud.user_profile_agent import UserProfileAgent
from agents.cloud.vector_knowledge_agent import VectorKnowledgeAgent
from agents.orchestrator.global_dispatch_agent import GlobalDispatchAgent
from agents.vehicle.local_intent_agent import LocalIntentAgent
from config.env_loader import load_env_file
from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.vehicle_core_service import VehicleCoreService
from data.vehicle_state_service import VehicleStateService
from data.vehicle_event_service import VehicleEventService
from evaluation.offline_evaluator import OfflineEvaluator
from feedback.feedback_service import FeedbackService
from llm.factory import create_llm_client
from llm.local_provider import create_local_llm_provider
from providers.destination_resolver import resolve_destination_detail
from providers.factory import (
    create_charge_provider,
    create_geocode_provider,
    create_map_provider,
    create_weather_provider,
)
from scripts.smoke_real_providers import run_smoke_checks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCEPTANCE_REPORT = PROJECT_ROOT / "reports" / "acceptance_report.md"
VEHICLE_STATE_SERVICE = VehicleStateService()
VEHICLE_EVENT_SERVICE = VehicleEventService()


USERS = [
    {"user_id": "user_001", "label": "user_001：舒适 + 高速偏好"},
    {"user_id": "user_002", "label": "user_002：音乐 + 补能提醒"},
]

SCENARIOS = [
    {"label": "导航去蔚来中心", "content": "导航去蔚来中心", "network": "ONLINE", "trigger": "MANUAL"},
    {"label": "打开座椅加热", "content": "打开座椅加热", "network": "OFFLINE", "trigger": "MANUAL"},
    {"label": "电量低（手动）", "content": "电量低", "network": "ONLINE", "trigger": "MANUAL"},
    {"label": "我的偏好", "content": "我的偏好", "network": "ONLINE", "trigger": "MANUAL"},
    {"label": "关闭AEB", "content": "关闭AEB", "network": "ONLINE", "trigger": "MANUAL"},
]

DEMO_STEPS = [
    {
        "id": "online_navigation",
        "title": "在线导航端云协同",
        "content": "导航去蔚来中心",
        "network": "ONLINE",
        "focus": "端云协同、RAG 召回、真实地图路线、DeepSeek 决策说明",
        "talk_track": (
            "这一步展示完整在线链路：车端先做本地意图识别和安全校验，"
            "通过后进入云端调度，组合用户画像、外部生态、路线规划和 LLM 最终说明。"
        ),
        "expected_panels": ["Agent 调用链", "RAG 召回知识", "路线与补能", "执行结果"],
    },
    {
        "id": "car_control_no_route",
        "title": "车控指令不误调地图",
        "content": "温度调到24度",
        "network": "ONLINE",
        "focus": "按意图分流，车控只走画像、生态和 LLM 决策，不调用 route.plan",
        "talk_track": (
            "这一步用来说明 Multi-Agent 编排不是所有 Agent 都调用。"
            "车控指令不会进入路线规划 Agent，避免把温度设置误解析成目的地。"
        ),
        "expected_panels": ["Agent 调用链", "Runtime Trace", "执行结果"],
    },
    {
        "id": "charge_planning",
        "title": "低电量补能规划",
        "content": "电量低",
        "network": "ONLINE",
        "focus": "补能 RAG、附近充电站 POI、路线规划、用户偏好高速",
        "talk_track": (
            "这一步展示补能场景：系统根据低电量知识召回补能建议，"
            "再结合高德 POI 找附近充电站，并用路线 Provider 规划可执行路线。"
        ),
        "expected_panels": ["RAG 召回知识", "路线与补能", "Provider 状态"],
    },
    {
        "id": "safety_block",
        "title": "危险指令安全拦截",
        "content": "关闭AEB",
        "network": "ONLINE",
        "focus": "SafetyAgent 与 SafetyPolicy 前置拦截，危险车控不进入云端执行链",
        "talk_track": (
            "这一步强调车载 AI 的安全边界。即使系统能识别这是车控指令，"
            "涉及 AEB 等安全能力时也必须被策略层拦截。"
        ),
        "expected_panels": ["Agent 调用链", "执行结果"],
    },
    {
        "id": "online_error_explain",
        "title": "真实接口失败解释",
        "content": "导航去巴黎",
        "network": "ONLINE",
        "focus": "在线模式不静默离线兜底，失败时给出可理解原因和建议",
        "talk_track": (
            "这一步展示真实 API 失败处理：高德无法规划跨境目的地时，"
            "系统不会编造结果，而是把技术错误转换成用户能理解的解释。"
        ),
        "expected_panels": ["错误说明", "Agent 调用链", "RAG 召回知识"],
    },
]


def get_initial_payload():
    load_env_file()
    event_payload = get_vehicle_events_payload()
    return {
        "vehicle_state": event_payload["vehicle_state"],
        "auto_events": event_payload["events"],
        "auto_event_rules": event_payload["event_rules"],
        "users": USERS,
        "scenarios": SCENARIOS,
        "demo_steps": get_demo_steps(),
        "cloud_tools": GlobalDispatchAgent().tool_registry.list_names(),
        "offline_evaluation": OfflineEvaluator().run(),
        "providers": _provider_status(),
        "acceptance": get_acceptance_payload(),
    }


def run_command(content: str, user_id: str = "user_001", network: str = "ONLINE"):
    load_env_file()
    network_status = _parse_network(network)
    service = _build_vehicle_service()
    result = service.run(content, user_id=user_id, network=network_status)
    should_show_route = result.status != ExecutionStatus.NEEDS_CLARIFICATION

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
            "clarification": result.clarification or {},
        },
        "feedback": result.feedback or {},
        "local_context": result.local_context or {},
        "graph": result.graph or {},
        "runtime_trace": result.trace or [],
        "route_summary": (
            _route_summary(content, result.message.command_type, result.message.network)
            if should_show_route
            else {}
        ),
        "charge_stations": (
            _charge_stations(result.message.command_type, result.message.network)
            if should_show_route
            else []
        ),
        "rag_context": _rag_context(
            result.message.content,
            result.message.user_id,
            result.message.command_type,
            result.message.network,
            include_route_context=should_show_route,
        ),
        "agent_trace": _agent_trace(result.message.command_type, result.message.safety, result.status),
    }


def update_vehicle_state(updates: dict):
    VEHICLE_STATE_SERVICE.update(updates or {})
    event_payload = get_vehicle_events_payload()
    return {
        "vehicle_state": event_payload["vehicle_state"],
        "auto_events": event_payload["events"],
        "auto_event_rules": event_payload["event_rules"],
    }


def reset_vehicle_state():
    VEHICLE_STATE_SERVICE.reset()


def get_vehicle_events_payload(network: str = "ONLINE"):
    network_status = _parse_network(network)
    return VEHICLE_EVENT_SERVICE.snapshot(
        VEHICLE_STATE_SERVICE.current_state(),
        network=network_status,
    )


def run_provider_smoke_test():
    load_env_file()
    return {"results": run_smoke_checks()}


def get_demo_steps():
    return [dict(step) for step in DEMO_STEPS]


def get_acceptance_payload(report_path=None):
    path = Path(report_path) if report_path else DEFAULT_ACCEPTANCE_REPORT
    if not path.exists():
        return {
            "available": False,
            "overall_status": "UNKNOWN",
            "generated_at": "",
            "steps": [],
            "report_path": str(path),
        }

    text = path.read_text(encoding="utf-8")
    return {
        "available": True,
        "overall_status": _extract_report_value(text, "- 总体状态：") or "UNKNOWN",
        "generated_at": _extract_report_value(text, "- 生成时间："),
        "steps": _parse_acceptance_steps(text),
        "report_path": str(path),
    }


def _parse_network(network: str) -> NetworkStatus:
    normalized = (network or "ONLINE").upper()
    if normalized == NetworkStatus.OFFLINE.value:
        return NetworkStatus.OFFLINE
    return NetworkStatus.ONLINE


def _build_vehicle_service(vehicle_state=None):
    return VehicleCoreService(
        feedback_service=FeedbackService(),
        vehicle_state=vehicle_state or VEHICLE_STATE_SERVICE.current_state(),
    )


def _extract_report_value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _parse_acceptance_steps(text: str):
    steps = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 3:
            continue
        if cells[0] in {"步骤", "---"} or set(cells[0]) == {"-"}:
            continue
        steps.append(
            {
                "name": cells[0],
                "status": cells[1],
                "duration": cells[2],
            }
        )
    return steps


def _vehicle_state_payload(network: NetworkStatus):
    return VEHICLE_STATE_SERVICE.to_payload(network)


def _agent_trace(command_type: CommandType, safety: SafetyLevel, status: ExecutionStatus):
    trace = ["LocalIntentAgent", "GlobalSafetyDispatchAgent"]

    if status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION:
        trace.append("DriverConfirmation")
        trace.append("DataUploadAgent")
        return trace

    if status == ExecutionStatus.NEEDS_CLARIFICATION:
        trace.append("DestinationClarification")
        trace.append("DataUploadAgent")
        return trace

    if safety == SafetyLevel.DANGEROUS or status == ExecutionStatus.BLOCKED:
        trace.append("SafetyBlock")
        return trace

    if status == ExecutionStatus.FALLBACK:
        if command_type == CommandType.NAVIGATION:
            trace.append("CabinVehicleControlAgent")
        elif command_type == CommandType.CAR_CONTROL:
            trace.append("CabinVehicleControlAgent")
        else:
            trace.append("LocalFallback")
        trace.append("DataUploadAgent")
        return trace

    trace.extend(
        [
            "GlobalDispatchAgent",
            "UserProfileAgent",
            "VectorKnowledgeAgent",
        ]
    )
    if command_type in {CommandType.NAVIGATION, CommandType.CHARGE_PLAN}:
        trace.append("ExternalEcologyAgent")
        trace.append("GlobalTripPlanningAgent")
    trace.append("DataUploadAgent")
    return trace


def _rag_context(
    content: str,
    user_id: str,
    command_type: CommandType,
    network: NetworkStatus,
    include_route_context: bool = True,
):
    context = []

    intent_agent = LocalIntentAgent()
    for result in intent_agent.retrieve_context(content):
        context.append(_context_payload("本地意图识别", result))

    if network == NetworkStatus.ONLINE and command_type in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
        CommandType.CAR_CONTROL,
        CommandType.PERSONALIZE,
        CommandType.INFO_QUERY,
    }:
        profile_agent = UserProfileAgent()
        for result in profile_agent.retrieve_context(user_id, content):
            context.append(_context_payload("用户画像召回", result))

        knowledge_agent = VectorKnowledgeAgent()
        for result in knowledge_agent.retrieve(content, user_id=user_id, command_type=command_type):
            context.append(_context_payload("向量知识库召回", result))

    if include_route_context and network == NetworkStatus.ONLINE and command_type in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
    }:
        route_agent = GlobalTripPlanningAgent()
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


def _provider_status():
    orchestrator = GlobalDispatchAgent()
    return {
        "llm": create_llm_client().provider_name,
        "local_llm": create_local_llm_provider().provider_name,
        "orchestrator": (
            "langgraph_default"
            if orchestrator.enable_langgraph
            else "lightweight_forced"
        ),
        "map": create_map_provider().provider_name,
        "weather": create_weather_provider().provider_name,
        "charge": create_charge_provider().provider_name,
    }


def _route_summary(content: str, command_type: CommandType, network: NetworkStatus):
    if network != NetworkStatus.ONLINE or command_type not in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
    }:
        return {}

    destination = resolve_destination_detail(content, geocoder=create_geocode_provider())
    vehicle_state = VEHICLE_STATE_SERVICE.current_state()
    route = create_map_provider().plan_route(
        vehicle_state.gps,
        destination.gps,
        preference="高速",
    )
    return {
        "provider": route.provider,
        "destination_name": destination.name,
        "destination_gps": destination.gps,
        "destination_source": destination.source,
        "distance_km": route.distance_km,
        "duration_minutes": route.duration_minutes,
        "strategy": route.strategy,
    }


def _charge_stations(command_type: CommandType, network: NetworkStatus):
    if network != NetworkStatus.ONLINE or command_type not in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
    }:
        return []

    vehicle_state = VEHICLE_STATE_SERVICE.current_state()
    stations = create_charge_provider().find_nearby(vehicle_state.gps, limit=3)
    return [
        {
            "name": station.name,
            "distance_km": station.distance_km,
            "status": station.status,
            "estimated_minutes": station.estimated_minutes,
        }
        for station in stations
    ]
