import os
import unittest
from dataclasses import is_dataclass
from unittest.mock import patch

from config.settings import AppSettings, get_settings


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

    def test_defaults_match_existing_factory_getenv_behavior(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

        self.assertIsNone(settings.amap_api_key)
        self.assertIsNone(settings.baidu_map_ak)
        self.assertEqual(settings.amap_geocode_city, "")
        self.assertIsNone(settings.use_open_meteo)
        self.assertEqual(settings.open_charge_map_api_key, "")
        self.assertIsNone(settings.use_open_charge_map)

    def test_get_settings_reads_current_environment_each_call(self):
        with patch.dict(os.environ, {"AMAP_API_KEY": "first"}, clear=True):
            first = get_settings()
        with patch.dict(os.environ, {"AMAP_API_KEY": "second"}, clear=True):
            second = get_settings()

        self.assertEqual(first.amap_api_key, "first")
        self.assertEqual(second.amap_api_key, "second")


if __name__ == "__main__":
    unittest.main()
