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


class EdgeDeepSeekSimProvider:
    provider_name = "edge_deepseek_sim"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        timeout: int = 8,
        max_output_tokens: int = 64,
        context_limit_tokens: int = 7500,
        generation_buffer_tokens: int = 500,
        transport=None,
    ):
        if not api_key:
            raise ValueError("DeepSeek api_key is required for edge_deepseek_sim")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = int(timeout)
        self.max_output_tokens = max(1, int(max_output_tokens))
        self.context_limit_tokens = max(1, int(context_limit_tokens))
        self.generation_buffer_tokens = max(0, int(generation_buffer_tokens))
        self.transport = transport or _post_json

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        url = f"{self.base_url}/chat/completions"
        prompt_budget_tokens = max(
            64,
            self.context_limit_tokens - self.generation_buffer_tokens,
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\n\n"
                        "Runtime: edge local LLM simulation. Keep reasoning brief, "
                        "use only the supplied single-agent context, and return a "
                        "short result suitable for an in-vehicle small model."
                    ),
                },
                {
                    "role": "user",
                    "content": _compose_budgeted_user_content(
                        user_prompt=user_prompt,
                        context=context or {},
                        prompt_budget_tokens=prompt_budget_tokens,
                    ),
                },
            ],
            "temperature": 0.1,
            "max_tokens": self.max_output_tokens,
            "thinking": {"type": "disabled"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = self.transport(
            url,
            headers,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            self.timeout,
        )
        return response["choices"][0]["message"]["content"].strip()


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

    if provider in {"edge_deepseek_sim", "deepseek_edge", "edge_deepseek"}:
        return EdgeDeepSeekSimProvider(
            api_key=os.getenv("LOCAL_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("LOCAL_LLM_DEEPSEEK_BASE_URL")
            or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=model
            or os.getenv("DEEPSEEK_EDGE_MODEL", "").strip()
            or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            timeout=timeout,
            max_output_tokens=_env_int("LOCAL_LLM_MAX_OUTPUT_TOKENS", 64),
            context_limit_tokens=_env_int("LOCAL_LLM_MAX_CONTEXT_TOKENS", 7500),
            generation_buffer_tokens=_env_int(
                "LOCAL_LLM_GENERATION_BUFFER_TOKENS",
                500,
            ),
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


def _compose_budgeted_user_content(
    user_prompt: str,
    context: dict,
    prompt_budget_tokens: int,
) -> str:
    full_content = _compose_user_content(user_prompt, context)
    if _estimate_tokens(full_content) <= prompt_budget_tokens:
        return full_content

    compact_context = {
        "current_input": context.get("current_input", ""),
        "summary": _tail(context.get("summary", ""), 240),
        "recent_turns": _compact_recent_turns(context.get("recent_turns", [])),
        "preference_state": context.get("preference_state", {}),
        "vehicle_state": context.get("vehicle_state", {}),
        "retrieved_context": _compact_retrieved_context(
            context.get("retrieved_context", [])
        ),
        "window": context.get("window", {}),
    }
    content = (
        f"{user_prompt}\n\n"
        "context truncated for edge budget\n"
        f"structured_context:\n{json.dumps(compact_context, ensure_ascii=False, indent=2, default=str)}"
    )
    max_chars = max(1, prompt_budget_tokens * 2)
    if len(content) <= max_chars:
        return content
    return content[: max(0, max_chars - 3)] + "..."


def _compact_recent_turns(turns):
    compacted = []
    for turn in list(turns or [])[-2:]:
        compacted.append(
            {
                "user_input": _tail(turn.get("user_input", ""), 80),
                "command_type": turn.get("command_type", ""),
                "safety": turn.get("safety", ""),
                "execution_status": turn.get("execution_status", ""),
            }
        )
    return compacted


def _compact_retrieved_context(items):
    compacted = []
    for item in list(items or [])[:2]:
        compacted.append(
            {
                "doc_id": item.get("doc_id", ""),
                "text": _tail(item.get("text", ""), 120),
                "score": item.get("score", 0),
            }
        )
    return compacted


def _tail(value, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return "..." + text[-(limit - 3) :]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 2)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return int(default)
    try:
        return int(raw)
    except ValueError:
        return int(default)


def _post_json(url: str, headers: dict, body: bytes, timeout: int):
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
