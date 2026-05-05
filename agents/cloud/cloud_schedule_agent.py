from agents.cloud.cloud_ecology_agent import CloudEcologyAgent
from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from core.constants import CommandType
from core.message import Message
from llm.factory import create_llm_client
from runtime.agent_runtime import AgentRuntime
from runtime.tool_schema import FieldSpec, ToolSpec
from runtime.tool_registry import ToolRegistry


class CloudScheduleAgent:
    def __init__(
        self,
        user_agent=None,
        route_agent=None,
        ecology_agent=None,
        llm_client=None,
        tool_registry=None,
        runtime=None,
    ):
        self.user_agent = user_agent or CloudUserProfileAgent()
        self.route_agent = route_agent or CloudRoutePlanAgent()
        self.ecology_agent = ecology_agent or CloudEcologyAgent()
        self.llm_client = llm_client or create_llm_client()
        self.tool_registry = tool_registry or self._build_tool_registry()
        self.runtime = runtime or AgentRuntime()

    def dispatch(self, msg: Message) -> str:
        self.runtime.reset()
        user_pref = self.runtime.call_tool(
            self.tool_registry,
            "user_profile.lookup",
            {"user_id": msg.user_id},
        )
        task_context = self._non_route_context(msg.command_type)
        route_preference = ""
        if self._requires_route(msg.command_type):
            route_preference = self.runtime.call_tool(
                self.tool_registry,
                "user_profile.route_preference",
                {"user_id": msg.user_id, "content": msg.content},
            )
        ecology = self.runtime.call_tool(self.tool_registry, "ecology.snapshot", {})
        if self._requires_route(msg.command_type):
            task_context = self.runtime.call_tool(
                self.tool_registry,
                "route.plan",
                {"content": msg.content, "route_preference": route_preference},
            )
            for provider_trace in self.route_agent.get_last_provider_trace():
                self.runtime.append_trace(**provider_trace)
        decision = self.runtime.call_tool(
            self.tool_registry,
            "decision.summarize",
            {
                "content": msg.content,
                "command_type": msg.command_type.value,
                "user_profile": user_pref,
                "ecology": ecology,
                "task_context": task_context,
            },
        )
        return f"{user_pref} | {ecology} | {task_context} | 云端决策：{decision}"

    def get_last_trace(self):
        return self.runtime.snapshot()

    def _requires_route(self, command_type: CommandType) -> bool:
        return command_type in {CommandType.NAVIGATION, CommandType.CHARGE_PLAN}

    def _non_route_context(self, command_type: CommandType) -> str:
        if command_type == CommandType.CAR_CONTROL:
            return "车控执行上下文：本次指令仅涉及座舱/车辆舒适控制，不调用地图路线规划。"
        if command_type == CommandType.PERSONALIZE:
            return "个性化上下文：本次指令仅查询用户画像与偏好，不调用地图路线规划。"
        return "通用执行上下文：本次指令不需要地图路线规划。"

    def _build_tool_registry(self):
        registry = ToolRegistry()
        registry.register(
            "user_profile.lookup",
            lambda payload: self.user_agent.get_profile(payload["user_id"]),
            spec=ToolSpec(input_fields=[FieldSpec("user_id", str)]),
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
        registry.register("ecology.snapshot", lambda payload: self.ecology_agent.get_data())
        registry.register(
            "route.plan",
            lambda payload: self.route_agent.plan(
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
                    "你是车载云端调度 Agent。请基于用户画像、外部生态、"
                    "指令类型与任务上下文生成最终执行说明。导航/补能指令可以引用路线结果，"
                    "车控/个性化指令不要编造地图路线，并保持简洁、遵守安全边界。"
                ),
                user_prompt=f"用户指令：{payload['content']}",
                context={
                    "command_type": payload["command_type"],
                    "user_profile": payload["user_profile"],
                    "ecology": payload["ecology"],
                    "task_context": payload["task_context"],
                },
            ),
            spec=ToolSpec(
                input_fields=[
                    FieldSpec("content", str),
                    FieldSpec("command_type", str),
                    FieldSpec("user_profile", str),
                    FieldSpec("ecology", str),
                    FieldSpec("task_context", str),
                ]
            ),
        )
        return registry
