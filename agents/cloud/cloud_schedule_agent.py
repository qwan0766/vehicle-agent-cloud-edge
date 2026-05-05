from agents.cloud.cloud_ecology_agent import CloudEcologyAgent
from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
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
        route_preference = self.runtime.call_tool(
            self.tool_registry,
            "user_profile.route_preference",
            {"user_id": msg.user_id, "content": msg.content},
        )
        ecology = self.runtime.call_tool(self.tool_registry, "ecology.snapshot", {})
        route = self.runtime.call_tool(
            self.tool_registry,
            "route.plan",
            {"content": msg.content, "route_preference": route_preference},
        )
        decision = self.runtime.call_tool(
            self.tool_registry,
            "decision.summarize",
            {
                "content": msg.content,
                "user_profile": user_pref,
                "ecology": ecology,
                "route": route,
            },
        )
        return f"{user_pref} | {ecology} | {route} | 云端决策：{decision}"

    def get_last_trace(self):
        return self.runtime.snapshot()

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
                    "路线规划结果生成最终执行说明，保持简洁并遵守安全边界。"
                ),
                user_prompt=f"用户指令：{payload['content']}",
                context={
                    "user_profile": payload["user_profile"],
                    "ecology": payload["ecology"],
                    "route": payload["route"],
                },
            ),
            spec=ToolSpec(
                input_fields=[
                    FieldSpec("content", str),
                    FieldSpec("user_profile", str),
                    FieldSpec("ecology", str),
                    FieldSpec("route", str),
                ]
            ),
        )
        return registry
