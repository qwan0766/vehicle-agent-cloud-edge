import os
from dataclasses import dataclass

from agents.vehicle.safety_agent import SafetyAgent
from core.constants import ExecutionStatus, SafetyLevel
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


@dataclass(frozen=True)
class CloudResultSafetyDecision:
    allowed: bool
    reason: str = ""
    status: ExecutionStatus = ExecutionStatus.EXECUTED
    risk_level: str = "LOW"
    source: str = "rule"
    sanitized_output: str = ""


class GlobalSafetyDispatchAgent:
    role_name = "全局安全调度 Agent"

    def __init__(
        self,
        keyword_agent=None,
        policy=None,
        local_llm_provider=None,
        enable_llm_explanations=None,
        enable_cloud_result_llm_review=None,
    ):
        self.keyword_agent = keyword_agent or SafetyAgent()
        self.policy = policy or SafetyPolicy()
        self.local_llm_provider = local_llm_provider
        self.enable_llm_explanations = (
            os.getenv("ENABLE_LOCAL_LLM_SAFETY_EXPLAIN") == "1"
            if enable_llm_explanations is None
            else bool(enable_llm_explanations)
        )
        self.enable_cloud_result_llm_review = (
            os.getenv("ENABLE_LOCAL_LLM_CLOUD_REVIEW") == "1"
            if enable_cloud_result_llm_review is None
            else bool(enable_cloud_result_llm_review)
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
        decision = self.verify_cloud_result_decision(result_text)
        return decision.allowed, decision.reason

    def verify_cloud_result_decision(
        self,
        result_text: str,
        command_type=None,
        vehicle_state=None,
    ) -> CloudResultSafetyDecision:
        if self._contains_actionable_dangerous_command(result_text):
            return CloudResultSafetyDecision(
                allowed=False,
                reason="云端结果包含危险控制词，已由车端安全调度 Agent 拦截",
                status=ExecutionStatus.BLOCKED,
                risk_level="HIGH",
                source="rule",
                sanitized_output="",
            )
        if self.enable_cloud_result_llm_review and self._needs_local_llm_review(result_text):
            return self._review_cloud_result_with_local_llm(
                result_text,
                command_type=command_type,
                vehicle_state=vehicle_state,
            )
        return CloudResultSafetyDecision(
            allowed=True,
            reason="",
            status=ExecutionStatus.EXECUTED,
            risk_level="LOW",
            source="rule",
            sanitized_output=result_text or "",
        )

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

    def _needs_local_llm_review(self, content: str) -> bool:
        normalized = (content or "").replace(" ", "")
        ambiguous_markers = (
            "执行",
            "控制",
            "巡航",
            "目标",
            "制动",
            "加速",
            "转向",
            "AEB",
            "确认",
        )
        return any(marker in normalized for marker in ambiguous_markers)

    def _review_cloud_result_with_local_llm(
        self,
        result_text: str,
        command_type=None,
        vehicle_state=None,
    ) -> CloudResultSafetyDecision:
        provider = self.local_llm_provider or create_local_llm_provider()
        context = self.build_local_safety_context(
            result_text,
            command_type=command_type,
            vehicle_state=vehicle_state,
        )
        try:
            raw = provider.generate(
                system_prompt=(
                    "You are the in-vehicle GlobalSafetyDispatchAgent. "
                    "Review cloud output before it reaches the execution layer. "
                    "Return exactly one label at the beginning: ALLOW, BLOCK, or CONFIRM. "
                    "Do not create executable vehicle-control instructions."
                ),
                user_prompt=f"cloud_output: {result_text}",
                context=context,
            ).strip()
        except Exception:
            return CloudResultSafetyDecision(
                allowed=True,
                reason="",
                status=ExecutionStatus.EXECUTED,
                risk_level="LOW",
                source="rule_fallback",
                sanitized_output=result_text or "",
            )

        normalized = raw.upper()
        if normalized.startswith("BLOCK"):
            return CloudResultSafetyDecision(
                allowed=False,
                reason=_extract_llm_reason(raw) or "本地安全小模型判定云端结果存在执行风险",
                status=ExecutionStatus.BLOCKED,
                risk_level="HIGH",
                source="local_llm",
                sanitized_output="",
            )
        if normalized.startswith("CONFIRM"):
            return CloudResultSafetyDecision(
                allowed=True,
                reason=_extract_llm_reason(raw) or "本地安全小模型要求驾驶员确认",
                status=ExecutionStatus.NEEDS_DRIVER_CONFIRMATION,
                risk_level="MEDIUM",
                source="local_llm",
                sanitized_output=result_text or "",
            )
        return CloudResultSafetyDecision(
            allowed=True,
            reason="",
            status=ExecutionStatus.EXECUTED,
            risk_level="LOW",
            source="local_llm",
            sanitized_output=result_text or "",
        )

    def build_local_safety_context(self, result_text: str, command_type=None, vehicle_state=None):
        return {
            "memory_scope": "agent_local",
            "agent_id": "global_safety_dispatch",
            "review_scope": "cloud_result",
            "command_type": getattr(command_type, "value", str(command_type or "")),
            "vehicle_state": vehicle_state or {},
            "cloud_output_preview": (result_text or "")[:1000],
            "policy": {
                "hard_rule_first": True,
                "local_llm_is_advisory": True,
                "final_execution_requires_rule_gate": True,
            },
        }


def _extract_llm_reason(raw: str) -> str:
    if ":" in raw:
        return raw.split(":", 1)[1].strip()
    if "：" in raw:
        return raw.split("：", 1)[1].strip()
    return ""


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
