import json
import os
from urllib import request


class MockLocalLLMProvider:
    provider_name = "mock_local"

    def __init__(self, model: str = "mock-local-intent"):
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        context = context or {}
        content = (
            context.get("current_input")
            or user_prompt.replace("用户指令：", "")
            or ""
        )
        normalized = content.lower()
        if any(keyword in normalized for keyword in ["导航", "去", "回家", "公司"]):
            return "NAVIGATION"
        if any(keyword in normalized for keyword in ["电量", "补能", "充电", "换电"]):
            return "CHARGE_PLAN"
        if any(keyword in normalized for keyword in ["座椅", "温度", "空调", "车窗"]):
            return "CAR_CONTROL"
        if any(keyword in normalized for keyword in ["偏好", "画像", "个性化"]):
            return "PERSONALIZE"
        return "UNKNOWN"


class OllamaLocalLLMProvider:
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:1.5b",
        timeout: int = 8,
        transport=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = int(timeout)
        self.transport = transport or _post_json

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": _compose_prompt(system_prompt, user_prompt, context or {}),
            "stream": False,
            "options": {"temperature": 0.1},
        }
        response = self.transport(
            url,
            {"Content-Type": "application/json"},
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            self.timeout,
        )
        return str(response.get("response", "")).strip()


class OpenAICompatibleLocalLLMProvider:
    def __init__(
        self,
        provider_name: str,
        base_url: str,
        model: str = "local-model",
        timeout: int = 8,
        transport=None,
    ):
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = int(timeout)
        self.transport = transport or _post_json

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": _compose_user_content(user_prompt, context or {}),
                },
            ],
            "temperature": 0.1,
        }
        response = self.transport(
            url,
            {"Content-Type": "application/json"},
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            self.timeout,
        )
        return response["choices"][0]["message"]["content"].strip()


def create_local_llm_provider():
    provider = os.getenv("LOCAL_LLM_PROVIDER", "mock_local").strip().lower()
    model = os.getenv("LOCAL_LLM_MODEL", "").strip()
    timeout = int(os.getenv("LOCAL_LLM_TIMEOUT", "8"))

    if provider in {"mock", "mock_local", "none", ""}:
        return MockLocalLLMProvider(model=model or "mock-local-intent")

    if provider == "ollama":
        return OllamaLocalLLMProvider(
            base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434"),
            model=model or "qwen2.5:1.5b",
            timeout=timeout,
        )

    if provider == "lmstudio":
        return OpenAICompatibleLocalLLMProvider(
            provider_name="lmstudio",
            base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
            model=model or "local-model",
            timeout=timeout,
        )

    if provider in {"llama_cpp", "llama.cpp", "llamacpp"}:
        return OpenAICompatibleLocalLLMProvider(
            provider_name="llama_cpp",
            base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8080/v1"),
            model=model or "local-model",
            timeout=timeout,
        )

    raise ValueError(f"Unsupported LOCAL_LLM_PROVIDER: {provider}")


def _compose_prompt(system_prompt: str, user_prompt: str, context: dict) -> str:
    return (
        f"{system_prompt}\n\n"
        f"{user_prompt}\n\n"
        f"结构化上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def _compose_user_content(user_prompt: str, context: dict) -> str:
    return (
        f"{user_prompt}\n\n"
        f"结构化上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def _post_json(url: str, headers: dict, body: bytes, timeout: int):
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

