import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class LLMSettings:
    deepseek_api_key: Optional[str] = field(default=None, repr=False)
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_base_url: str = "https://api.deepseek.com"

    @property
    def deepseek_configured(self) -> bool:
        return bool(self.deepseek_api_key)


@dataclass(frozen=True)
class LocalLLMSettings:
    provider: str = "mock_local"
    model: str = ""
    timeout: int = 8
    api_key: Optional[str] = field(default=None, repr=False)
    base_url: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    edge_model: str = ""
    max_output_tokens: int = 64
    context_limit_tokens: int = 7500
    generation_buffer_tokens: int = 500


@dataclass(frozen=True)
class ProviderSettings:
    amap_api_key: Optional[str] = field(default=None, repr=False)
    baidu_map_ak: Optional[str] = field(default=None, repr=False)
    amap_geocode_city: str = ""
    use_open_meteo: bool = False
    open_charge_map_api_key: str = field(default="", repr=False)
    use_open_charge_map: bool = False

    @property
    def amap_configured(self) -> bool:
        return bool(self.amap_api_key)

    @property
    def baidu_configured(self) -> bool:
        return bool(self.baidu_map_ak)

    @property
    def open_charge_map_configured(self) -> bool:
        return bool(self.open_charge_map_api_key) or self.use_open_charge_map


@dataclass(frozen=True)
class ProviderRuntimeSettings:
    timeout_seconds: int = 10
    retries: int = 1
    backoff_seconds: float = 0.1
    circuit_failure_threshold: int = 3
    circuit_reset_seconds: float = 30.0
    health_ttl_seconds: float = 30.0


@dataclass(frozen=True)
class RuntimeSettings:
    enable_langgraph: bool = True
    enable_llm_intent_fallback: bool = False
    enable_local_llm_input_rewrite: bool = False
    enable_local_llm_safety_explain: bool = False
    enable_local_llm_cloud_review: bool = False
    enable_local_llm_control_explain: bool = False


@dataclass(frozen=True)
class AppSettings:
    llm: LLMSettings
    local_llm: LocalLLMSettings
    providers: ProviderSettings
    runtime: RuntimeSettings
    provider_runtime: ProviderRuntimeSettings = field(default_factory=ProviderRuntimeSettings)

    @property
    def amap_api_key(self) -> Optional[str]:
        return self.providers.amap_api_key

    @property
    def baidu_map_ak(self) -> Optional[str]:
        return self.providers.baidu_map_ak

    @property
    def amap_geocode_city(self) -> str:
        return self.providers.amap_geocode_city

    @property
    def use_open_meteo(self) -> Optional[str]:
        return "1" if self.providers.use_open_meteo else None

    @property
    def open_charge_map_api_key(self) -> str:
        return self.providers.open_charge_map_api_key

    @property
    def use_open_charge_map(self) -> Optional[str]:
        return "1" if self.providers.use_open_charge_map else None


def get_settings() -> AppSettings:
    return AppSettings(
        llm=LLMSettings(
            deepseek_api_key=_env_optional("DEEPSEEK_API_KEY"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        ),
        local_llm=LocalLLMSettings(
            provider=os.getenv("LOCAL_LLM_PROVIDER", "mock_local").strip().lower(),
            model=os.getenv("LOCAL_LLM_MODEL", "").strip(),
            timeout=_env_int("LOCAL_LLM_TIMEOUT", 8),
            api_key=_env_optional("LOCAL_LLM_API_KEY") or _env_optional("DEEPSEEK_API_KEY"),
            base_url=os.getenv("LOCAL_LLM_BASE_URL", "").strip(),
            deepseek_base_url=(
                os.getenv("LOCAL_LLM_DEEPSEEK_BASE_URL")
                or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            ),
            edge_model=os.getenv("DEEPSEEK_EDGE_MODEL", "").strip(),
            max_output_tokens=_env_int("LOCAL_LLM_MAX_OUTPUT_TOKENS", 64),
            context_limit_tokens=_env_int("LOCAL_LLM_MAX_CONTEXT_TOKENS", 7500),
            generation_buffer_tokens=_env_int("LOCAL_LLM_GENERATION_BUFFER_TOKENS", 500),
        ),
        providers=ProviderSettings(
            amap_api_key=_env_optional("AMAP_API_KEY"),
            baidu_map_ak=_env_optional("BAIDU_MAP_AK"),
            amap_geocode_city=os.getenv("AMAP_GEOCODE_CITY", ""),
            use_open_meteo=_env_bool("USE_OPEN_METEO", False),
            open_charge_map_api_key=os.getenv("OPENCHARGEMAP_API_KEY", ""),
            use_open_charge_map=_env_bool("USE_OPENCHARGEMAP", False),
        ),
        runtime=RuntimeSettings(
            enable_langgraph=_env_bool("ENABLE_LANGGRAPH", True),
            enable_llm_intent_fallback=_env_bool("ENABLE_LLM_INTENT_FALLBACK", False),
            enable_local_llm_input_rewrite=_env_bool("ENABLE_LOCAL_LLM_INPUT_REWRITE", False),
            enable_local_llm_safety_explain=_env_bool("ENABLE_LOCAL_LLM_SAFETY_EXPLAIN", False),
            enable_local_llm_cloud_review=_env_bool("ENABLE_LOCAL_LLM_CLOUD_REVIEW", False),
            enable_local_llm_control_explain=_env_bool("ENABLE_LOCAL_LLM_CONTROL_EXPLAIN", False),
        ),
        provider_runtime=ProviderRuntimeSettings(
            timeout_seconds=_env_int("PROVIDER_TIMEOUT_SECONDS", 10),
            retries=_env_int("PROVIDER_RETRIES", 1),
            backoff_seconds=_env_float("PROVIDER_BACKOFF_SECONDS", 0.1),
            circuit_failure_threshold=_env_int("PROVIDER_CIRCUIT_FAILURE_THRESHOLD", 3),
            circuit_reset_seconds=_env_float("PROVIDER_CIRCUIT_RESET_SECONDS", 30.0),
            health_ttl_seconds=_env_float("PROVIDER_HEALTH_TTL_SECONDS", 30.0),
        ),
    )


def _env_optional(name: str) -> Optional[str]:
    value = os.getenv(name, "").strip()
    return value or None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return bool(default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return int(default)
    try:
        return int(value)
    except ValueError:
        return int(default)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    if not value:
        return float(default)
    try:
        return float(value)
    except ValueError:
        return float(default)
