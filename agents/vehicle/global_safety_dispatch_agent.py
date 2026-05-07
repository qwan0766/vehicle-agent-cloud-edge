import os

from agents.vehicle.safety_agent import SafetyAgent
from core.constants import SafetyLevel
from llm.local_provider import create_local_llm_provider
from safety.safety_policy import SafetyPolicy


ACTIONABLE_DANGEROUS_PATTERNS = [
    "加速到",
    "立即加速",
    "提升动力",
    "动力提升",
    "立即刹车",
    "执行刹车",
    "紧急制动",
    "执行制动",
    "关闭AEB",
    "关闭aeb",
    "禁用AEB",
    "禁用aeb",
    "关闭自动紧急制动",
    "禁用自动紧急制动",
    "接管方向盘",
    "自动转向",
    "执行转向",
]


class GlobalSafetyDispatchAgent:
    role_name = "全局安全调度 Agent"

    def __init__(
        self,
        keyword_agent=None,
        policy=None,
        local_llm_provider=None,
        enable_llm_explanations=None,
    ):
        self.keyword_agent = keyword_agent or SafetyAgent()
        self.policy = policy or SafetyPolicy()
        self.local_llm_provider = local_llm_provider
        self.enable_llm_explanations = (
            os.getenv("ENABLE_LOCAL_LLM_SAFETY_EXPLAIN") == "1"
            if enable_llm_explanations is None
            else bool(enable_llm_explanations)
        )

    def check(self, content: str) -> SafetyLevel:
        return self.keyword_agent.check(content)

    def evaluate(self, command_type, safety, network, content, vehicle_state=None):
        return self.policy.evaluate(
            command_type=command_type,
            safety=safety,
            network=network,
            content=content,
            vehicle_state=vehicle_state,
        )

    def verify_cloud_result(self, result_text: str):
        if self._contains_actionable_dangerous_command(result_text):
            return False, "云端结果包含危险控制词，已由车端安全调度 Agent 拦截"
        return True, ""

    def explain_blocked_command(self, content: str, command_type, policy_reason: str) -> str:
        if not self.enable_llm_explanations:
            return policy_reason
        provider = self.local_llm_provider or create_local_llm_provider()
        try:
            explanation = provider.generate(
                system_prompt=(
                    "You are the in-vehicle GlobalSafetyDispatchAgent. "
                    "Explain why the command is blocked in concise Chinese. "
                    "Do not create any executable vehicle-control instruction."
                ),
                user_prompt=f"blocked command: {content}",
                context={
                    "agent_id": "global_safety_dispatch",
                    "command_type": getattr(command_type, "value", str(command_type)),
                    "policy_reason": policy_reason,
                    "provider_role": "edge_local_safety_explainer",
                },
            )
        except Exception:
            return policy_reason
        return explanation.strip() or policy_reason

    def _contains_actionable_dangerous_command(self, content: str) -> bool:
        normalized = (content or "").replace(" ", "")
        if _looks_like_non_actionable_explanation(normalized):
            explicit_actions = tuple(
                pattern
                for pattern in ACTIONABLE_DANGEROUS_PATTERNS
                if pattern not in {"紧急制动"}
            )
            return any(pattern in normalized for pattern in explicit_actions)
        return any(pattern in normalized for pattern in ACTIONABLE_DANGEROUS_PATTERNS)


def _looks_like_non_actionable_explanation(normalized: str) -> bool:
    explanation_markers = (
        "信息查询",
        "功能说明",
        "不会执行车控动作",
        "不执行车控动作",
        "不执行车辆控制",
        "不是执行指令",
        "解释",
        "是什么",
        "含义",
    )
    return any(marker in normalized for marker in explanation_markers)
