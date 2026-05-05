import unittest

from agents.vehicle.local_intent_agent import LocalIntentAgent
from core.constants import CommandType


class FakeIntentLLM:
    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        return "NAVIGATION"


class TestLLMIntentFallback(unittest.TestCase):
    def test_unknown_intent_can_use_optional_llm_fallback(self):
        agent = LocalIntentAgent(
            llm_client=FakeIntentLLM(),
            enable_llm_fallback=True,
        )

        self.assertEqual(agent.recognize("带我去公司"), CommandType.NAVIGATION)

    def test_dangerous_keyword_is_not_sent_to_llm_fallback(self):
        agent = LocalIntentAgent(
            llm_client=FakeIntentLLM(),
            enable_llm_fallback=True,
        )

        self.assertEqual(agent.recognize("立即刹车"), CommandType.CAR_CONTROL)


if __name__ == "__main__":
    unittest.main()
