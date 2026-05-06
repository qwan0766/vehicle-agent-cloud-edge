import unittest
import uuid
from pathlib import Path

from agents.vehicle.local_intent_agent import LocalIntentAgent
from core.constants import CommandType, NetworkStatus
from core.vehicle_core_service import VehicleCoreService
from memory.local_context_manager import LocalContextManager
from web_demo.app_model import run_command


class CapturingLocalLLM:
    provider_name = "test_local"
    model = "tiny-intent"

    def __init__(self):
        self.calls = []

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "context": context or {},
            }
        )
        return "NAVIGATION"


class TestLocalLLMContextIntegration(unittest.TestCase):
    def test_local_context_contains_llm_prompt_envelope(self):
        path = Path(".test_runtime") / f"agent_context_{uuid.uuid4().hex}.json"
        manager = LocalContextManager(path=path, max_recent_turns=2)
        llm = CapturingLocalLLM()
        agent = LocalIntentAgent(
            local_llm_provider=llm,
            context_manager=manager,
        )

        context = agent.build_local_llm_context(
            user_id="user_001",
            current_input="打开座椅加热",
            vehicle_state={"speed_kmh": 60, "network": "OFFLINE"},
            preference_state={"route_preference": "高速"},
        )

        self.assertEqual(context["local_llm"]["provider"], "test_local")
        self.assertEqual(context["local_llm"]["model"], "tiny-intent")
        self.assertIn("system_prompt", context["local_llm"])
        self.assertIn("prompt_preview", context["local_llm"])
        self.assertIn("打开座椅加热", context["local_llm"]["prompt_preview"])
        self.assertGreater(context["window"]["estimated_prompt_tokens"], 0)

    def test_llm_intent_fallback_receives_local_context_package(self):
        llm = CapturingLocalLLM()
        agent = LocalIntentAgent(
            local_llm_provider=llm,
            enable_llm_fallback=True,
        )

        result = agent.recognize("处理一下这个需求", user_id="user_001")

        self.assertEqual(result, CommandType.NAVIGATION)
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(llm.calls[0]["context"]["agent_id"], "local_intent")
        self.assertEqual(llm.calls[0]["context"]["current_input"], "处理一下这个需求")
        self.assertIn("retrieved_context", llm.calls[0]["context"])

    def test_vehicle_service_passes_user_id_into_local_intent_context(self):
        path = Path(".test_runtime") / f"agent_context_{uuid.uuid4().hex}.json"
        manager = LocalContextManager(path=path)
        llm = CapturingLocalLLM()
        intent_agent = LocalIntentAgent(
            local_llm_provider=llm,
            context_manager=manager,
        )
        service = VehicleCoreService(
            context_manager=manager,
            intent_agent=intent_agent,
        )

        result = service.run(
            "打开座椅加热",
            user_id="user_002",
            network=NetworkStatus.OFFLINE,
        )

        self.assertEqual(result.local_context["user_id"], "user_002")
        self.assertEqual(result.local_context["agent_id"], "local_intent")
        self.assertIn("local_llm", result.local_context)

    def test_web_payload_exposes_local_llm_context_for_offline_runs(self):
        payload = run_command(
            "打开座椅加热",
            user_id=f"user_{uuid.uuid4().hex}",
            network="OFFLINE",
        )

        self.assertIn("local_llm", payload["local_context"])
        self.assertIn("prompt_preview", payload["local_context"]["local_llm"])
        self.assertIn("estimated_prompt_tokens", payload["local_context"]["window"])


if __name__ == "__main__":
    unittest.main()
