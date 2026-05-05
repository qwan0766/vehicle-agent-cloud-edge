import os
import unittest
from unittest.mock import patch

from providers.baidu_map_provider import BaiduMapProvider
from providers.factory import create_charge_provider, create_map_provider, create_weather_provider
from providers.offline_charge_provider import OfflineChargeProvider
from providers.offline_map_provider import OfflineMapProvider
from providers.offline_weather_provider import OfflineWeatherProvider
from providers.open_charge_map_provider import OpenChargeMapProvider
from providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


class TestProviderFactory(unittest.TestCase):
    def test_defaults_to_offline_providers(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(create_map_provider(), OfflineMapProvider)
            self.assertIsInstance(create_weather_provider(), OfflineWeatherProvider)
            self.assertIsInstance(create_charge_provider(), OfflineChargeProvider)

    def test_uses_real_providers_when_env_is_available(self):
        with patch.dict(
            os.environ,
            {
                "BAIDU_MAP_AK": "map-key",
                "USE_OPEN_METEO": "1",
                "OPENCHARGEMAP_API_KEY": "charge-key",
            },
            clear=True,
        ):
            self.assertIsInstance(create_map_provider(), BaiduMapProvider)
            self.assertIsInstance(create_weather_provider(), OpenMeteoWeatherProvider)
            self.assertIsInstance(create_charge_provider(), OpenChargeMapProvider)


if __name__ == "__main__":
    unittest.main()
