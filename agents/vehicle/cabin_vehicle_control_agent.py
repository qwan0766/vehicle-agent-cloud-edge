import os

from agents.vehicle.car_control_agent import CarControlAgent
from agents.vehicle.nav_agent import NavAgent
from core.constants import CommandType
from llm.local_provider import create_local_llm_provider


class CabinVehicleControlAgent:
    role_name = "座舱/车控 Agent"

    def __init__(
        self,
        car_control_agent=None,
        nav_agent=None,
        local_llm_provider=None,
        enable_llm_explanations=None,
    ):
        self.car_control_agent = car_control_agent or CarControlAgent()
        self.nav_agent = nav_agent or NavAgent()
        self.local_llm_provider = local_llm_provider
        self.enable_llm_explanations = (
            os.getenv("ENABLE_LOCAL_LLM_CONTROL_EXPLAIN") == "1"
            if enable_llm_explanations is None
            else bool(enable_llm_explanations)
        )

    def _append_control_explanation(
        self,
        output: str,
        command_type: CommandType,
        command: str,
        local_context=None,
    ) -> str:
        if not self.enable_llm_explanations:
            return output
        provider = self.local_llm_provider or create_local_llm_provider()
        source_context = local_context or {}
        try:
            explanation = provider.generate(
                system_prompt=(
                    "You are the in-vehicle CabinVehicleControlAgent. "
                    "Explain the completed cabin control action in concise Chinese. "
                    "Do not add new vehicle-control instructions."
                ),
                user_prompt=f"completed local command: {command}",
                context={
                    "agent_id": "cabin_vehicle_control",
                    "source_context_agent": source_context.get("agent_id", ""),
                    "command_type": command_type.value,
                    "base_execution_output": output,
                    "source_context_summary": source_context.get("summary", ""),
                    "provider_role": "edge_local_control_explainer",
                },
            )
        except Exception:
            return output
        explanation = explanation.strip()
        if not explanation:
            return output
        return f"{output}\n{explanation}"

    def execute(self, command_type: CommandType, command: str, local_context=None) -> str:
        if command_type == CommandType.CAR_CONTROL:
            output = self.car_control_agent.execute(command)
            return self._append_control_explanation(
                output,
                command_type,
                command,
                local_context,
            )
        if command_type == CommandType.NAVIGATION:
            return self.nav_agent.start(command)
        if command_type == CommandType.CHARGE_PLAN:
            return "断网模式：根据本地知识库建议前往最近换电站"
        if command_type == CommandType.PERSONALIZE:
            return self._local_personalize_response(local_context)
        return "断网模式：当前指令无法本地执行"

    def _local_personalize_response(self, local_context) -> str:
        context = local_context or {}
        recent_count = len(context.get("recent_turns", []))
        summary = context.get("summary") or "暂无压缩摘要"
        preferences = context.get("preference_state") or {}
        preference_text = (
            "、".join(f"{key}={value}" for key, value in preferences.items())
            if preferences
            else "暂无动态偏好"
        )
        return (
            "断网模式：使用本地用户画像与本地意图 Agent 上下文。\n"
            f"- 历史摘要：{summary}\n"
            f"- 最近交互：{recent_count} 条\n"
            f"- 动态偏好：{preference_text}"
        )
