import json
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

from agents.vehicle.input_rewrite_agent import InputRewriteAgent
from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.message import Message
from memory.local_agent_context_manager import LocalAgentContextManager


class FakeRewriteLLM:
    provider_name = "edge_deepseek_sim"
    model = "deepseek-edge-lite"

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "context": context or {},
            }
        )
        return json.dumps(self.payload, ensure_ascii=False)


class TestInputRewriteAgent(unittest.TestCase):
    def test_edge_llm_rewrite_returns_structured_payload(self):
        llm = FakeRewriteLLM(
            {
                "rewritten_input": "导航去北京蔚来中心",
                "intent_hint": "NAVIGATION",
                "slots": {"destination": "北京蔚来中心", "city": "北京"},
                "confidence": 0.86,
                "needs_clarification": False,
                "reason": "补全导航动作",
            }
        )
        agent = InputRewriteAgent(local_llm_provider=llm, enable_llm_rewrite=True)

        result = agent.rewrite(
            "去北京的蔚来中心",
            user_id="user_001",
            preference_state={"route_preference": "高速"},
            vehicle_state={"speed_kmh": 60},
        )

        self.assertEqual(result.raw_input, "去北京的蔚来中心")
        self.assertEqual(result.rewritten_input, "导航去北京蔚来中心")
        self.assertEqual(result.intent_hint, CommandType.NAVIGATION)
        self.assertEqual(result.slots["city"], "北京")
        self.assertFalse(result.needs_clarification)
        self.assertEqual(result.source, "local_llm")
        self.assertEqual(llm.calls[0]["context"]["agent_id"], "input_rewrite")

    def test_rule_fallback_uses_recent_navigation_memory_for_reference(self):
        path = Path(".test_runtime") / f"rewrite_context_{uuid.uuid4().hex}.json"
        manager = LocalAgentContextManager(path=path, max_recent_turns=4)
        previous = SimpleNamespace(
            status=ExecutionStatus.EXECUTED,
            output="已规划前往北京蔚来中心的路线",
            message=Message.create(
                user_id="user_001",
                command_type=CommandType.NAVIGATION,
                safety=SafetyLevel.SAFE,
                content="导航去北京蔚来中心",
                network=NetworkStatus.ONLINE,
            ),
        )
        manager.record_result(previous, agent_id="local_intent")
        agent = InputRewriteAgent(
            context_manager=manager,
            enable_llm_rewrite=False,
        )

        result = agent.rewrite("去刚才那个地方", user_id="user_001")

        self.assertEqual(result.rewritten_input, "导航去北京蔚来中心")
        self.assertEqual(result.intent_hint, CommandType.NAVIGATION)
        self.assertIn("recent_turns", result.memory_used)
        self.assertEqual(result.source, "rule")


if __name__ == "__main__":
    unittest.main()
