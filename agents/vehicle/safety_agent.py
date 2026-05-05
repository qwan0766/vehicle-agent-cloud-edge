from core.constants import SafetyLevel
from data.knowledge_base import DANGEROUS_KEYWORDS


class SafetyAgent:
    def check(self, content: str) -> SafetyLevel:
        normalized = (content or "").lower()
        for keyword in DANGEROUS_KEYWORDS:
            if keyword.lower() in normalized:
                return SafetyLevel.DANGEROUS
        return SafetyLevel.SAFE
