from core.constants import SafetyLevel
from data.knowledge_base import DANGEROUS_KEYWORDS


class SafetyAgent:
    def check(self, content: str) -> SafetyLevel:
        if _contains_actionable_dangerous_control(content):
            return SafetyLevel.DANGEROUS
        if _contains_dangerous_keyword(content) and _looks_like_vehicle_control(content):
            return SafetyLevel.DANGEROUS
        return SafetyLevel.SAFE


def _contains_dangerous_keyword(content: str) -> bool:
    normalized = (content or "").lower()
    return any(keyword.lower() in normalized for keyword in DANGEROUS_KEYWORDS)


def _looks_like_vehicle_control(content: str) -> bool:
    normalized = (content or "").replace(" ", "").lower()
    if _looks_like_non_actionable_question(normalized):
        return False
    action_words = (
        "关闭",
        "禁用",
        "打开",
        "开启",
        "执行",
        "立即",
        "接管",
        "调高",
        "调低",
        "提升",
        "降低",
        "帮我",
    )
    return any(action in normalized for action in action_words)


def _looks_like_non_actionable_question(normalized: str) -> bool:
    question_markers = (
        "是什么",
        "什么意思",
        "介绍",
        "讲一下",
        "解释",
        "为什么",
        "如何",
        "?",
        "？",
    )
    return any(marker in normalized for marker in question_markers)


def _contains_actionable_dangerous_control(content: str) -> bool:
    normalized = (content or "").replace(" ", "").lower()
    actionable_patterns = (
        "加速到",
        "立即加速",
        "提升动力",
        "动力提升",
        "立即刹车",
        "执行刹车",
        "紧急制动",
        "执行制动",
        "立即制动",
        "关闭aeb",
        "禁用aeb",
        "关闭自动紧急制动",
        "禁用自动紧急制动",
        "接管方向盘",
        "自动转向",
        "执行转向",
        "帮我转向",
    )
    return any(pattern in normalized for pattern in actionable_patterns)
