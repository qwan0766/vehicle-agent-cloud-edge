from config.settings import get_settings
from llm.deepseek_client import DeepSeekLLMClient
from llm.mock_llm_client import MockLLMClient


def create_llm_client(settings=None):
    settings = settings or get_settings()
    api_key = settings.llm.deepseek_api_key
    if api_key:
        return DeepSeekLLMClient(
            api_key=api_key,
            model=settings.llm.deepseek_model,
            base_url=settings.llm.deepseek_base_url,
        )
    return MockLLMClient()
