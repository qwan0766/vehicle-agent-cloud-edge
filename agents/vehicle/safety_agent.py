from core.constants import SafetyLevel
from data.knowledge_base import DANGEROUS_KEYWORDS


class SafetyAgent:
    def check(self, content: str) -> SafetyLevel:
        for keyword in DANGEROUS_KEYWORDS:
            if keyword in content:
                return SafetyLevel.DANGEROUS
        return SafetyLevel.SAFE
