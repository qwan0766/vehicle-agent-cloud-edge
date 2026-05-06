import json
import unittest
from unittest.mock import patch

from llm.local_provider import (
    MockLocalLLMProvider,
    OllamaLocalLLMProvider,
    OpenAICompatibleLocalLLMProvider,
    create_local_llm_provider,
)


class TestLocalLLMProvider(unittest.TestCase):
    def test_factory_defaults_to_mock_local_provider(self):
        with patch.dict("os.environ", {}, clear=True):
            provider = create_local_llm_provider()

        self.assertIsInstance(provider, MockLocalLLMProvider)
        self.assertEqual(provider.provider_name, "mock_local")
        self.assertEqual(provider.model, "mock-local-intent")

    def test_factory_builds_ollama_provider_from_env(self):
        with patch.dict(
            "os.environ",
            {
                "LOCAL_LLM_PROVIDER": "ollama",
                "LOCAL_LLM_MODEL": "qwen2.5:1.5b",
                "LOCAL_LLM_BASE_URL": "http://127.0.0.1:11434",
            },
            clear=True,
        ):
            provider = create_local_llm_provider()

        self.assertIsInstance(provider, OllamaLocalLLMProvider)
        self.assertEqual(provider.provider_name, "ollama")
        self.assertEqual(provider.model, "qwen2.5:1.5b")

    def test_ollama_provider_builds_generate_request_with_context(self):
        captured = {}

        def fake_transport(url, headers, body, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json.loads(body.decode("utf-8"))
            return {"response": "NAVIGATION"}

        provider = OllamaLocalLLMProvider(
            base_url="http://127.0.0.1:11434",
            model="qwen2.5:1.5b",
            transport=fake_transport,
        )

        result = provider.generate(
            system_prompt="你是本地意图 Agent",
            user_prompt="用户指令：带我去公司",
            context={"current_input": "带我去公司", "summary": "用户经常走高速"},
        )

        self.assertEqual(result, "NAVIGATION")
        self.assertEqual(captured["url"], "http://127.0.0.1:11434/api/generate")
        self.assertEqual(captured["headers"]["Content-Type"], "application/json")
        self.assertEqual(captured["body"]["model"], "qwen2.5:1.5b")
        self.assertFalse(captured["body"]["stream"])
        self.assertIn("用户经常走高速", captured["body"]["prompt"])

    def test_openai_compatible_provider_builds_chat_completion_request(self):
        captured = {}

        def fake_transport(url, headers, body, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json.loads(body.decode("utf-8"))
            return {
                "choices": [
                    {"message": {"content": "CAR_CONTROL"}},
                ]
            }

        provider = OpenAICompatibleLocalLLMProvider(
            provider_name="lmstudio",
            base_url="http://127.0.0.1:1234/v1",
            model="local-model",
            transport=fake_transport,
        )

        result = provider.generate(
            system_prompt="你是本地意图 Agent",
            user_prompt="用户指令：打开座椅加热",
            context={"current_input": "打开座椅加热"},
        )

        self.assertEqual(result, "CAR_CONTROL")
        self.assertEqual(captured["url"], "http://127.0.0.1:1234/v1/chat/completions")
        self.assertEqual(captured["body"]["model"], "local-model")
        self.assertIn("结构化上下文", captured["body"]["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
