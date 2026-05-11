import json
import unittest

from config.settings import (
    AppSettings,
    LLMSettings,
    LocalLLMSettings,
    ProviderSettings,
    RuntimeSettings,
)
from llm.deepseek_client import DeepSeekLLMClient
from llm.factory import create_llm_client
from llm.mock_llm_client import MockLLMClient


class TestLLMClients(unittest.TestCase):
    def test_mock_llm_generates_deterministic_decision(self):
        client = MockLLMClient()

        result = client.generate(
            system_prompt="你是车载云端决策 Agent",
            user_prompt="请规划路线",
            context={"route_hint": "长途优先高速路线"},
        )

        self.assertIn("LLM决策", result)
        self.assertIn("长途优先高速路线", result)

    def test_deepseek_client_builds_openai_compatible_request(self):
        captured = {}

        def fake_transport(url, headers, body, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json.loads(body.decode("utf-8"))
            return {
                "choices": [
                    {"message": {"content": "DeepSeek 路线决策结果"}},
                ]
            }

        client = DeepSeekLLMClient(
            api_key="test-key",
            model="deepseek-v4-flash",
            transport=fake_transport,
        )

        result = client.generate(
            system_prompt="system",
            user_prompt="user",
            context={"a": 1},
        )

        self.assertEqual(result, "DeepSeek 路线决策结果")
        self.assertEqual(captured["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(captured["body"]["model"], "deepseek-v4-flash")
        self.assertEqual(captured["body"]["thinking"], {"type": "disabled"})

    def test_llm_factory_uses_structured_settings(self):
        settings = AppSettings(
            llm=LLMSettings(
                deepseek_api_key="test-key",
                deepseek_model="deepseek-test",
                deepseek_base_url="https://example.deepseek.local",
            ),
            local_llm=LocalLLMSettings(),
            providers=ProviderSettings(),
            runtime=RuntimeSettings(),
        )

        client = create_llm_client(settings=settings)

        self.assertIsInstance(client, DeepSeekLLMClient)
        self.assertEqual(client.model, "deepseek-test")
        self.assertEqual(client.base_url, "https://example.deepseek.local")


if __name__ == "__main__":
    unittest.main()
