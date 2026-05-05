import json
import unittest

from llm.deepseek_client import DeepSeekLLMClient
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


if __name__ == "__main__":
    unittest.main()
