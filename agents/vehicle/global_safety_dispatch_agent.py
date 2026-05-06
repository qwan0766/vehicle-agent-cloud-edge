from agents.vehicle.safety_agent import SafetyAgent
from core.constants import SafetyLevel
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

    def __init__(self, keyword_agent=None, policy=None):
        self.keyword_agent = keyword_agent or SafetyAgent()
        self.policy = policy or SafetyPolicy()

    def check(self, content: str) -> SafetyLevel:
        return self.keyword_agent.check(content)

    def evaluate(self, command_type, safety, network, content):
        return self.policy.evaluate(
            command_type=command_type,
            safety=safety,
            network=network,
            content=content,
        )

    def verify_cloud_result(self, result_text: str):
        if self._contains_actionable_dangerous_command(result_text):
            return False, "云端结果包含危险控制词，已由车端安全调度 Agent 拦截"
        return True, ""

    def _contains_actionable_dangerous_command(self, content: str) -> bool:
        normalized = (content or "").replace(" ", "")
        return any(pattern in normalized for pattern in ACTIONABLE_DANGEROUS_PATTERNS)
