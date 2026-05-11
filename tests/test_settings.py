import os
import unittest
from dataclasses import is_dataclass
from unittest.mock import patch

from config.settings import (
    AppSettings,
    LLMSettings,
    LocalLLMSettings,
    ProviderSettings,
    RuntimeSettings,
    get_settings,
)


class TestAppSettings(unittest.TestCase):
    def test_reads_provider_factory_environment(self):
        with patch.dict(
            os.environ,
            {
                "AMAP_API_KEY": "amap-key",
                "BAIDU_MAP_AK": "baidu-key",
                "AMAP_GEOCODE_CITY": "shanghai",
                "USE_OPEN_METEO": "1",
                "OPENCHARGEMAP_API_KEY": "charge-key",
                "USE_OPENCHARGEMAP": "1",
                "DEEPSEEK_API_KEY": "deepseek-key",
                "DEEPSEEK_MODEL": "deepseek-chat",
                "LOCAL_LLM_PROVIDER": "edge_deepseek_sim",
                "LOCAL_LLM_MAX_CONTEXT_TOKENS": "2048",
                "LOCAL_LLM_MAX_OUTPUT_TOKENS": "32",
                "ENABLE_LANGGRAPH": "0",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertIsInstance(settings, AppSettings)
        self.assertTrue(is_dataclass(settings))
        self.assertEqual(settings.amap_api_key, "amap-key")
        self.assertEqual(settings.baidu_map_ak, "baidu-key")
        self.assertEqual(settings.amap_geocode_city, "shanghai")
        self.assertEqual(settings.use_open_meteo, "1")
        self.assertEqual(settings.open_charge_map_api_key, "charge-key")
        self.assertEqual(settings.use_open_charge_map, "1")
        self.assertIsInstance(settings.llm, LLMSettings)
        self.assertIsInstance(settings.local_llm, LocalLLMSettings)
        self.assertIsInstance(settings.providers, ProviderSettings)
        self.assertIsInstance(settings.runtime, RuntimeSettings)
        self.assertEqual(settings.llm.deepseek_model, "deepseek-chat")
        self.assertTrue(settings.llm.deepseek_configured)
        self.assertEqual(settings.local_llm.provider, "edge_deepseek_sim")
        self.assertEqual(settings.local_llm.context_limit_tokens, 2048)
        self.assertEqual(settings.local_llm.max_output_tokens, 32)
        self.assertFalse(settings.runtime.enable_langgraph)

    def test_defaults_match_existing_factory_getenv_behavior(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

        self.assertIsNone(settings.amap_api_key)
        self.assertIsNone(settings.baidu_map_ak)
        self.assertEqual(settings.amap_geocode_city, "")
        self.assertIsNone(settings.use_open_meteo)
        self.assertEqual(settings.open_charge_map_api_key, "")
        self.assertIsNone(settings.use_open_charge_map)
        self.assertEqual(settings.local_llm.provider, "mock_local")
        self.assertEqual(settings.local_llm.timeout, 8)
        self.assertTrue(settings.runtime.enable_langgraph)

    def test_get_settings_reads_current_environment_each_call(self):
        with patch.dict(os.environ, {"AMAP_API_KEY": "first"}, clear=True):
            first = get_settings()
        with patch.dict(os.environ, {"AMAP_API_KEY": "second"}, clear=True):
            second = get_settings()

        self.assertEqual(first.amap_api_key, "first")
        self.assertEqual(second.amap_api_key, "second")

    def test_settings_repr_does_not_leak_secret_values(self):
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "deepseek-secret",
                "LOCAL_LLM_API_KEY": "local-secret",
                "AMAP_API_KEY": "amap-secret",
                "BAIDU_MAP_AK": "baidu-secret",
                "OPENCHARGEMAP_API_KEY": "charge-secret",
            },
            clear=True,
        ):
            settings = get_settings()

        rendered = repr(settings)

        self.assertNotIn("deepseek-secret", rendered)
        self.assertNotIn("local-secret", rendered)
        self.assertNotIn("amap-secret", rendered)
        self.assertNotIn("baidu-secret", rendered)
        self.assertNotIn("charge-secret", rendered)

    def test_bool_and_int_environment_parsing_is_tolerant(self):
        with patch.dict(
            os.environ,
            {
                "ENABLE_LANGGRAPH": "false",
                "USE_OPEN_METEO": "true",
                "LOCAL_LLM_TIMEOUT": "bad-int",
                "LOCAL_LLM_MAX_CONTEXT_TOKENS": "bad-int",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertFalse(settings.runtime.enable_langgraph)
        self.assertTrue(settings.providers.use_open_meteo)
        self.assertEqual(settings.local_llm.timeout, 8)
        self.assertEqual(settings.local_llm.context_limit_tokens, 7500)


if __name__ == "__main__":
    unittest.main()
