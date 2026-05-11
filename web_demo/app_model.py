from pathlib import Path

from agents.cloud.vector_knowledge_agent import VectorKnowledgeAgent
from agents.orchestrator.global_dispatch_agent import GlobalDispatchAgent
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
        "display_mode": "端云协同",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 35,
            "driver_assist_mode": "ACC",
        },
        "focus": "端云协同、RAG 召回、真实地图路线、DeepSeek 决策说明",
        "talk_track": (
            "这一步展示完整在线链路：车端先做本地意图识别和安全校验，"
            "通过后进入云端调度，组合用户画像、外部生态、路线规划和 LLM 最终说明。"
        ),
        "expected_panels": ["Agent 调用链", "RAG 召回知识", "路线与补能", "执行结果"],
    },
    {
        "id": "fuzzy_destination_clarification",
        "title": "模糊目的地澄清",
        "content": "导航去北京",
        "network": "OFFLINE",
        "display_mode": "本地澄清",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 35,
            "driver_assist_mode": "ACC",
        },
        "focus": "目的地只有城市级信息时进入 NEEDS_CLARIFICATION，不直接调用地图规划",
        "talk_track": (
            "这一步展示业务状态建模：导航意图已明确，但目的地不够具体。"
            "系统会要求用户补充门店、商圈或完整地址，而不是把低置信度结果直接执行。"
        ),
        "expected_panels": ["执行结果", "Agent 调用链", "RAG 召回知识"],
    },
    {
        "id": "highway_speed_confirmation",
        "title": "高速速度请求确认",
        "content": "加速到100km/h",
        "network": "OFFLINE",
        "display_mode": "驾驶员确认",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 35,
            "driver_assist_mode": "ACC",
        },
        "focus": "同样是速度请求，高速限速 120 场景下进入驾驶员确认，而不是直接动力控制",
        "talk_track": (
            "这一步回应车载安全细节：系统不会直接执行加速，"
            "但在高速且目标速度未超限时，可以转化为巡航目标确认。"
        ),
        "expected_panels": ["车辆状态", "Agent 调用链", "执行结果"],
    },
    {
        "id": "urban_speed_block",
        "title": "城市超限危险拦截",
        "content": "加速到100km/h",
        "network": "OFFLINE",
        "display_mode": "安全前置拦截",
        "vehicle_state": {
            "road_type": "URBAN",
            "speed_limit_kmh": 60,
            "speed_kmh": 40,
            "battery_percent": 35,
            "driver_assist_mode": "MANUAL",
        },
        "focus": "同一句速度请求切换到城市限速 60 后变成 BLOCKED，体现状态驱动安全策略",
        "talk_track": (
            "这一步展示车辆上下文不是展示字段，而是决策输入。"
            "道路类型和限速变化后，系统会拦截超限速度请求。"
        ),
        "expected_panels": ["车辆状态", "Agent 调用链", "执行结果"],
    },
    {
        "id": "low_battery_energy_policy",
        "title": "低电量状态与能源策略",
        "content": "导航去蔚来中心",
        "network": "OFFLINE",
        "display_mode": "状态触发 · 能源策略",
        "vehicle_state": {
            "road_type": "HIGHWAY",
            "speed_limit_kmh": 120,
            "speed_kmh": 60,
            "battery_percent": 8,
            "driver_assist_mode": "ACC",
        },
        "focus": "严重低电量由状态事件主动提示，并在导航前进入补能确认",
        "talk_track": (
            "这一步展示低电量不是用户输入按钮，而是车辆状态事件。"
            "当电量进入 critical 区间时，EnergyPolicyAgent 会要求先确认补能规划。"
        ),
        "expected_panels": ["车辆状态", "Agent 调用链", "执行结果", "路线与补能"],
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
        "offline_evaluation": _pending_offline_evaluation_payload(),
        "providers": _provider_status(),
        "acceptance": get_acceptance_payload(),
    }


def get_offline_evaluation_payload():
    report = dict(OfflineEvaluator().run())
    report["status"] = "READY"
    return report


def _pending_offline_evaluation_payload():
    return {
        "status": "PENDING",
        "total": 0,
        "intent_accuracy": 0,
        "safety_block_recall": 0,
        "rag_hit_rate": 0,
    }


def run_command(content: str, user_id: str = "user_001", network: str = "ONLINE"):
    load_env_file()
    network_status = _parse_network(network)
    service = _build_vehicle_service()
    result = service.run(content, user_id=user_id, network=network_status)
    return _command_payload(result, network_status)


def confirm_pending_action(
    action_id: str,
    user_id: str = "user_001",
    confirmed: bool = True,
    selection: dict = None,
):
    load_env_file()
    service = _build_vehicle_service()
    result = service.confirm_pending_action(
        action_id,
        user_id=user_id,
        confirmed=confirmed,
        selection=selection or {},
    )
    return _command_payload(result, result.message.network)


def _command_payload(result, network_status: NetworkStatus):
    content = result.message.content
    should_show_route = result.status not in {
        ExecutionStatus.NEEDS_CLARIFICATION,
        ExecutionStatus.NEEDS_CHARGE_CONFIRMATION,
    }

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
        "input_rewrite": result.input_rewrite or {},
        "result": {
            "status": result.status.value,
            "output": result.output,
            "clarification": result.clarification or {},
            "pending_action": result.pending_action or {},
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
        "agent_trace": _agent_trace(
            result.message.command_type,
            result.message.safety,
            result.status,
            result.output,
            result.trace or [],
        ),
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


def _agent_trace(
    command_type: CommandType,
    safety: SafetyLevel,
    status: ExecutionStatus,
    output: str = "",
    runtime_trace: list = None,
):
    trace = ["LocalIntentAgent", "GlobalSafetyDispatchAgent"]

    if status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION:
        trace.append("DriverConfirmation")
        trace.append("DataUploadAgent")
        return trace

    if status == ExecutionStatus.NEEDS_CHARGE_CONFIRMATION:
        trace.append("EnergyPolicyAgent")
        trace.append("DataUploadAgent")
        return trace

    if status == ExecutionStatus.NEEDS_CLARIFICATION:
        trace.append("DestinationClarification")
        trace.append("DataUploadAgent")
        return trace

    if status == ExecutionStatus.BLOCKED and _looks_like_energy_policy_output(output):
        trace.append("EnergyPolicyAgent")
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

    trace.extend(["GlobalDispatchAgent", "UserProfileAgent"])
    if _uses_rule_knowledge(command_type, runtime_trace or [], output):
        trace.append("RuleKnowledgeAgent")
    if _uses_document_rag(runtime_trace or [], output):
        trace.append("DocumentRAGAgent")
    if command_type in {CommandType.NAVIGATION, CommandType.CHARGE_PLAN}:
        trace.append("ExternalEcologyAgent")
        trace.append("RouteProviderAgent")
        trace.append("GlobalTripPlanningAgent")
    trace.append("CloudDecisionAgent")
    trace.append("DataUploadAgent")
    return trace


def _looks_like_energy_policy_output(output: str) -> bool:
    text = output or ""
    return "电量" in text or "低电量" in text or "补能" in text


def _uses_rule_knowledge(
    command_type: CommandType,
    runtime_trace: list,
    output: str,
) -> bool:
    if "规则知识库召回" in (output or ""):
        return True
    if command_type in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
        CommandType.CAR_CONTROL,
    }:
        return any(item.get("tool_name") == "knowledge.retrieve" for item in runtime_trace)
    return False


def _uses_document_rag(runtime_trace: list, output: str) -> bool:
    if "文档RAG召回" in (output or ""):
        return True
    for item in runtime_trace:
        if item.get("tool_name") != "knowledge.retrieve":
            continue
        tool_output = item.get("output", "")
        if isinstance(tool_output, str) and "文档RAG召回" in tool_output:
            return True
    return False


def _rag_context(
    content: str,
    user_id: str,
    command_type: CommandType,
    network: NetworkStatus,
    include_route_context: bool = True,
):
    context = []

    if network == NetworkStatus.ONLINE and command_type in {
        CommandType.NAVIGATION,
        CommandType.CHARGE_PLAN,
        CommandType.CAR_CONTROL,
        CommandType.PERSONALIZE,
        CommandType.INFO_QUERY,
    }:
        knowledge_agent = VectorKnowledgeAgent()
        for result in knowledge_agent.retrieve(
            content,
            user_id=user_id,
            command_type=command_type,
            top_k=3,
        ):
            context.append(_context_payload(_rag_stage(result), result))

    return context


def _rag_stage(result):
    doc_id = result.document.doc_id
    if doc_id.startswith("profile_"):
        return "用户画像召回"
    knowledge_type = result.document.metadata.get("knowledge_type")
    if knowledge_type == "structured_rule":
        return "规则知识库"
    if knowledge_type == "document_rag":
        return "文档RAG召回"
    return "知识库召回"


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
