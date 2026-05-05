import os

from llm.deepseek_client import DeepSeekLLMClient
from llm.mock_llm_client import MockLLMClient


def create_llm_client():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        return DeepSeekLLMClient(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        )
    return MockLLMClient()
