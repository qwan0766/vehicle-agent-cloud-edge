import unittest

from providers.baidu_map_provider import BaiduMapProvider
from providers.open_charge_map_provider import OpenChargeMapProvider
from providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


class TestRealProviderClients(unittest.TestCase):
    def test_baidu_map_provider_builds_driving_route_url(self):
        provider = BaiduMapProvider(api_key="map-key")

        url = provider.build_driving_route_url("31.23,121.48", "31.25,121.50")

        self.assertIn("https://api.map.baidu.com/direction/v2/driving", url)
        self.assertIn("origin=31.23%2C121.48", url)
        self.assertIn("destination=31.25%2C121.50", url)
        self.assertIn("ak=map-key", url)

    def test_open_meteo_provider_builds_forecast_url(self):
        provider = OpenMeteoWeatherProvider()

        url = provider.build_forecast_url("121.48, 31.23")

        self.assertIn("https://api.open-meteo.com/v1/forecast", url)
        self.assertIn("latitude=31.23", url)
        self.assertIn("longitude=121.48", url)
        self.assertIn("current=temperature_2m", url)

    def test_open_charge_map_provider_builds_poi_url(self):
        provider = OpenChargeMapProvider(api_key="charge-key")

        url = provider.build_poi_url("121.48, 31.23", limit=5)

        self.assertIn("https://api.openchargemap.io/v3/poi", url)
        self.assertIn("latitude=31.23", url)
        self.assertIn("longitude=121.48", url)
        self.assertIn("maxresults=5", url)
        self.assertIn("key=charge-key", url)


if __name__ == "__main__":
    unittest.main()
