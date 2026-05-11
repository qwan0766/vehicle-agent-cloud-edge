import os
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

from agents.cloud.external_ecology_agent import ExternalEcologyAgent
from agents.cloud.global_trip_planning_agent import GlobalTripPlanningAgent
from agents.cloud.user_profile_agent import UserProfileAgent
from agents.cloud.vector_knowledge_agent import VectorKnowledgeAgent
from core.constants import CommandType
from core.message import Message
from data.vehicle_state import DEFAULT_VEHICLE_STATE
from llm.factory import create_llm_client
from runtime.agent_runtime import AgentRuntime
from runtime.tool_registry import ToolRegistry
from runtime.tool_schema import FieldSpec, ToolSpec
from workflow.cloud_graph import LangGraphUnavailable, run_langgraph_cloud_workflow


class GlobalDispatchAgent:
    role_name = "全局调度 Agent"
    business_agent_count = 8

    def __init__(
        self,
        user_agent=None,
        route_agent=None,
        ecology_agent=None,
        knowledge_agent=None,
        llm_client=None,
        tool_registry=None,
        runtime=None,
        enable_langgraph=None,
    ):
        self.user_agent = user_agent or UserProfileAgent()
        self.route_agent = route_agent or GlobalTripPlanningAgent()
        self.ecology_agent = ecology_agent or ExternalEcologyAgent()
        self.knowledge_agent = knowledge_agent or VectorKnowledgeAgent()
        self.llm_client = llm_client or create_llm_client()
        self.tool_registry = tool_registry or self._build_tool_registry()
        self.runtime = runtime or AgentRuntime()
        self.enable_langgraph = (
            os.getenv("ENABLE_LANGGRAPH", "1") != "0"
            if enable_langgraph is None
            else bool(enable_langgraph)
        )
        self._last_graph = self._empty_graph_state()

    def dispatch(self, msg: Message) -> str:
        self.runtime.reset(request_id=msg.request_id)
        if self.enable_langgraph:
            try:
                state = run_langgraph_cloud_workflow(
                    self._initial_graph_state(msg),
                    self._graph_node_handlers(),
                    self._requires_trip_planning,
                )
            except LangGraphUnavailable as exc:
                return self._dispatch_lightweight(msg, fallback_reason=str(exc))
            self._last_graph = self._graph_metadata(
                mode="langgraph",
                path=state.get("path", []),
                fallback=False,
                backend="StateGraph",
                parallel_groups=state.get("parallel_groups", []),
            )
            return state["result"]
        return self._dispatch_lightweight(msg)

    def get_last_trace(self):
        return self.runtime.snapshot()

    def get_last_graph(self):
        return dict(self._last_graph)

    def _dispatch_lightweight(self, msg: Message, fallback_reason: str = "") -> str:
        state = self._initial_graph_state(msg)
        state = self._graph_context_parallel(state)
        if self._requires_trip_planning(msg.command_type):
            state = self._graph_provider_parallel(state)
            state = self._graph_trip_plan(state)
        state = self._graph_decision(state)
        state = self._graph_assemble(state)
        self._last_graph = self._graph_metadata(
            mode="lightweight",
            path=state.get("path", []),
            fallback=bool(fallback_reason),
            reason=fallback_reason,
            backend="python",
            parallel_groups=state.get("parallel_groups", []),
        )
        return state["result"]

    def _initial_graph_state(self, msg: Message) -> dict:
        return {
            "message": msg,
            "path": [],
            "parallel_groups": [],
            "route_preference": "",
            "task_context": "",
        }

    def _graph_node_handlers(self):
        return {
            "context_parallel": self._graph_context_parallel,
            "profile": self._graph_profile,
            "knowledge": self._graph_knowledge,
            "route_preference": self._graph_route_preference,
            "ecology": self._graph_ecology,
            "provider_parallel": self._graph_provider_parallel,
            "trip_plan": self._graph_trip_plan,
            "decision": self._graph_decision,
            "assemble": self._graph_assemble,
        }

    def _graph_context_parallel(self, state: dict) -> dict:
        msg = state["message"]
        updated = self._copy_state(state)
        tasks = [
            {
                "node": "profile",
                "tool_name": "user_profile.lookup",
                "payload": {"user_id": msg.user_id},
                "state_key": "user_profile",
            },
            {
                "node": "knowledge",
                "tool_name": "knowledge.retrieve",
                "payload": {
                    "content": msg.content,
                    "user_id": msg.user_id,
                    "command_type": msg.command_type.value,
                },
                "state_key": "knowledge_context",
            },
        ]
        if self._requires_trip_planning(msg.command_type):
            tasks.extend(
                [
                    {
                        "node": "route_preference",
                        "tool_name": "user_profile.route_preference",
                        "payload": {"user_id": msg.user_id, "content": msg.content},
                        "state_key": "route_preference",
                    },
                ]
            )

        outputs = self._run_parallel_tools(tasks)
        for task in tasks:
            tool_result = outputs[task["node"]]
            self.runtime.append_trace(
                tool_name=task["tool_name"],
                input=task["payload"],
                output=tool_result["output"],
                duration_ms=tool_result["duration_ms"],
            )
            updated[task["state_key"]] = tool_result["output"]

        updated["parallel_groups"] = [
            {
                "id": "cloud_context",
                "label": "云端并行上下文收集",
                "nodes": [task["node"] for task in tasks],
            }
        ]
        return self._mark_path(updated, "context_parallel")

    def _graph_provider_parallel(self, state: dict) -> dict:
        msg = state["message"]
        updated = self._copy_state(state)
        tasks = [
            {
                "node": "ecology",
                "tool_name": "ecology.snapshot",
                "payload": {"gps": DEFAULT_VEHICLE_STATE.gps},
                "state_key": "ecology_snapshot",
            },
            {
                "node": "route_provider",
                "tool_name": "route.context",
                "payload": {
                    "content": msg.content,
                    "route_preference": updated.get("route_preference", ""),
                },
                "state_key": "route_context",
            },
        ]
        outputs = self._run_parallel_tools(tasks)

        ecology_result = outputs["ecology"]
        self.runtime.append_trace(
            tool_name="ecology.snapshot",
            input=tasks[0]["payload"],
            output=ecology_result["output"],
            duration_ms=ecology_result["duration_ms"],
        )
        updated["ecology_snapshot"] = ecology_result["output"]
        updated["ecology"] = self.ecology_agent.format_snapshot(ecology_result["output"])

        route_result = outputs["route_provider"]["output"]
        for provider_trace in route_result.get("provider_trace", []):
            self.runtime.append_trace(**provider_trace)
        updated["route_context"] = {
            key: value
            for key, value in route_result.items()
            if key != "provider_trace"
        }
        updated["parallel_groups"].append(
            {
                "id": "route_provider_parallel",
                "label": "云端并行生态与路线工具",
                "nodes": ["ecology", "route_provider"],
            }
        )
        return self._mark_path(updated, "provider_parallel")

    def _run_parallel_tools(self, tasks: list) -> dict:
        if not tasks:
            return {}
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {
                task["node"]: executor.submit(
                    self._call_tool_without_trace,
                    task["tool_name"],
                    task["payload"],
                )
                for task in tasks
            }
            return {task["node"]: futures[task["node"]].result() for task in tasks}

    def _call_tool_without_trace(self, tool_name: str, payload: dict) -> dict:
        started = perf_counter()
        output = self.tool_registry.call(tool_name, payload)
        return {
            "output": output,
            "duration_ms": round((perf_counter() - started) * 1000, 3),
        }

    def _graph_profile(self, state: dict) -> dict:
        msg = state["message"]
        updated = self._copy_state(state)
        updated["user_profile"] = self.runtime.call_tool(
            self.tool_registry,
            "user_profile.lookup",
            {"user_id": msg.user_id},
        )
        return self._mark_path(updated, "profile")

    def _graph_knowledge(self, state: dict) -> dict:
        msg = state["message"]
        updated = self._copy_state(state)
        updated["knowledge_context"] = self.runtime.call_tool(
            self.tool_registry,
            "knowledge.retrieve",
            {
                "content": msg.content,
                "user_id": msg.user_id,
                "command_type": msg.command_type.value,
            },
        )
        return self._mark_path(updated, "knowledge")

    def _graph_route_preference(self, state: dict) -> dict:
        msg = state["message"]
        updated = self._copy_state(state)
        updated["route_preference"] = self.runtime.call_tool(
            self.tool_registry,
            "user_profile.route_preference",
            {"user_id": msg.user_id, "content": msg.content},
        )
        return self._mark_path(updated, "route_preference")

    def _graph_ecology(self, state: dict) -> dict:
        updated = self._copy_state(state)
        snapshot = self.runtime.call_tool(
            self.tool_registry,
            "ecology.snapshot",
            {"gps": DEFAULT_VEHICLE_STATE.gps},
        )
        updated["ecology_snapshot"] = snapshot
        updated["ecology"] = self.ecology_agent.format_snapshot(snapshot)
        return self._mark_path(updated, "ecology")

    def _graph_trip_plan(self, state: dict) -> dict:
        msg = state["message"]
        updated = self._copy_state(state)
        updated["task_context"] = self.runtime.call_tool(
            self.tool_registry,
            "trip.plan",
            {
                "content": msg.content,
                "route_preference": updated.get("route_preference", ""),
                "route_context": updated.get("route_context", {}),
            },
        )
        if not updated.get("route_context"):
            for provider_trace in self.route_agent.get_last_provider_trace():
                self.runtime.append_trace(**provider_trace)
        return self._mark_path(updated, "trip_plan")

    def _graph_decision(self, state: dict) -> dict:
        msg = state["message"]
        updated = self._copy_state(state)
        if not updated.get("task_context"):
            updated["task_context"] = self._non_route_context(msg.command_type)
        updated["decision"] = self.runtime.call_tool(
            self.tool_registry,
            "decision.summarize",
            {
                "content": msg.content,
                "command_type": msg.command_type.value,
                "user_profile": updated.get("user_profile", ""),
                "knowledge_context": updated.get("knowledge_context", ""),
                "ecology": updated.get("ecology", ""),
                "task_context": updated.get("task_context", ""),
            },
        )
        return self._mark_path(updated, "decision")

    def _graph_assemble(self, state: dict) -> dict:
        updated = self._copy_state(state)
        updated["result"] = self._assemble_result(updated)
        return self._mark_path(updated, "assemble")
        updated["result"] = (
            f"{updated.get('user_profile', '')} | "
            f"{updated.get('knowledge_context', '')} | "
            f"{updated.get('ecology', '')} | "
            f"{updated.get('task_context', '')} | "
            f"云端决策：{updated.get('decision', '')}"
        )
        return self._mark_path(updated, "assemble")

    def _copy_state(self, state: dict) -> dict:
        updated = dict(state)
        updated["path"] = list(state.get("path", []))
        updated["parallel_groups"] = [dict(group) for group in state.get("parallel_groups", [])]
        return updated

    def _assemble_result(self, state: dict) -> str:
        if self._requires_trip_planning(state["message"].command_type):
            return _dedupe_decision_text(
                state.get("decision", ""),
                state.get("task_context", ""),
            )
        return " | ".join(
            item
            for item in [
                state.get("user_profile", ""),
                state.get("knowledge_context", ""),
                state.get("ecology", ""),
                state.get("decision", ""),
            ]
            if item
        )

    def _mark_path(self, state: dict, node_name: str) -> dict:
        updated = self._copy_state(state)
        updated["path"].append(node_name)
        return updated

    def _graph_metadata(
        self,
        mode: str,
        path: list,
        fallback: bool,
        backend: str,
        reason: str = "",
        parallel_groups: list = None,
    ) -> dict:
        return {
            "enabled": self.enable_langgraph,
            "mode": mode,
            "backend": backend,
            "fallback": fallback,
            "reason": reason,
            "path": list(path),
            "parallel_groups": list(parallel_groups or []),
        }

    def _empty_graph_state(self) -> dict:
        return {
            "enabled": self.enable_langgraph if hasattr(self, "enable_langgraph") else False,
            "mode": "not_run",
            "backend": "",
            "fallback": False,
            "reason": "",
            "path": [],
            "parallel_groups": [],
        }

    def _requires_trip_planning(self, command_type: CommandType) -> bool:
        return command_type in {CommandType.NAVIGATION, CommandType.CHARGE_PLAN}

    def _requires_external_ecology(self, command_type: CommandType) -> bool:
        return self._requires_trip_planning(command_type)

    def _non_route_context(self, command_type: CommandType) -> str:
        if command_type == CommandType.CAR_CONTROL:
            return "座舱/车控上下文：本次指令仅涉及舒适控制，不调用地图路线规划。"
        if command_type == CommandType.PERSONALIZE:
            return "个性化上下文：本次指令查询用户画像与偏好，不调用地图路线规划。"
        if command_type == CommandType.INFO_QUERY:
            return "信息查询上下文：本次指令只需要解释车辆知识或功能含义，不调用地图路线规划，也不执行车控动作。"
        return "通用执行上下文：本次指令不需要地图路线规划。"

    def _build_tool_registry(self):
        registry = ToolRegistry()
        registry.register(
            "user_profile.lookup",
            lambda payload: self.user_agent.get_profile(payload["user_id"]),
            spec=ToolSpec(input_fields=[FieldSpec("user_id", str)]),
        )
        registry.register(
            "knowledge.retrieve",
            lambda payload: self.knowledge_agent.summarize(
                payload["content"],
                user_id=payload.get("user_id", ""),
                command_type=CommandType(payload.get("command_type", CommandType.UNKNOWN.value)),
            ),
            spec=ToolSpec(
                input_fields=[
                    FieldSpec("content", str),
                    FieldSpec("user_id", str, required=False),
                    FieldSpec("command_type", str, required=False),
                ]
            ),
        )
        registry.register(
            "user_profile.route_preference",
            lambda payload: self.user_agent.get_route_preference(
                payload["user_id"], payload.get("content", "")
            ),
            spec=ToolSpec(
                input_fields=[
                    FieldSpec("user_id", str),
                    FieldSpec("content", str, required=False),
                ]
            ),
        )
        registry.register(
            "ecology.snapshot",
            lambda payload: self.ecology_agent.get_snapshot(
                payload.get("gps") or DEFAULT_VEHICLE_STATE.gps
            ),
        )
        registry.register(
            "trip.plan",
            lambda payload: self.route_agent.plan(
                payload["content"],
                route_preference=payload.get("route_preference", ""),
                route_context=payload.get("route_context") or None,
            ),
            spec=ToolSpec(
                input_fields=[
                    FieldSpec("content", str),
                    FieldSpec("route_preference", str, required=False),
                    FieldSpec("route_context", dict, required=False),
                ]
            ),
        )
        registry.register(
            "route.context",
            lambda payload: self.route_agent.build_route_context(
                payload["content"],
                route_preference=payload.get("route_preference", ""),
            ),
            spec=ToolSpec(
                input_fields=[
                    FieldSpec("content", str),
                    FieldSpec("route_preference", str, required=False),
                ]
            ),
        )
        registry.register(
            "decision.summarize",
            lambda payload: self.llm_client.generate(
                system_prompt=(
                    "你是车载云端全局调度 Agent。请基于用户画像、向量知识库、"
                    "外部生态、指令类型与任务上下文生成最终执行说明。"
                    "导航/补能指令可以引用路线结果；车控/个性化指令不要编造地图路线；"
                    "所有结果必须遵守车端安全边界。"
                ),
                user_prompt=f"用户指令：{payload['content']}",
                context={
                    "command_type": payload["command_type"],
                    "user_profile": payload["user_profile"],
                    "knowledge_context": payload["knowledge_context"],
                    "ecology": payload["ecology"],
                    "task_context": payload["task_context"],
                },
            ),
            spec=ToolSpec(
                input_fields=[
                    FieldSpec("content", str),
                    FieldSpec("command_type", str),
                    FieldSpec("user_profile", str),
                    FieldSpec("knowledge_context", str),
                    FieldSpec("ecology", str),
                    FieldSpec("task_context", str),
                ]
            ),
        )
        return registry


def _dedupe_decision_text(decision: str, task_context: str) -> str:
    normalized_decision = (decision or "").strip()
    normalized_task = (task_context or "").strip()
    if not normalized_decision:
        return normalized_task
    prefixed_task = f"LLM决策：{normalized_task}"
    if normalized_task and normalized_decision.startswith(prefixed_task):
        suffix = normalized_decision[len(prefixed_task) :].strip()
        return f"{normalized_task}{suffix}" if suffix else normalized_task
    if normalized_task and normalized_decision.startswith(normalized_task):
        suffix = normalized_decision[len(normalized_task) :].strip()
        return f"{normalized_task}{suffix}" if suffix else normalized_task
    return normalized_decision
