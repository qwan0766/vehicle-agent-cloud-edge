import json
from urllib import request


class DeepSeekLLMClient:
    provider_name = "deepseek"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        timeout: int = 20,
        transport=None,
    ):
        if not api_key:
            raise ValueError("DeepSeek api_key is required")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
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
            "temperature": 0.2,
            "thinking": {"type": "disabled"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        response = self.transport(url, headers, body, self.timeout)
        return response["choices"][0]["message"]["content"].strip()


def _compose_user_content(user_prompt: str, context: dict) -> str:
    return (
        f"{user_prompt}\n\n"
        f"结构化上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def _post_json(url: str, headers: dict, body: bytes, timeout: int):
    req = request.Request(url, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))
