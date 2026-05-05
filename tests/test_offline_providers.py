import unittest

from providers.offline_charge_provider import OfflineChargeProvider
from providers.offline_weather_provider import OfflineWeatherProvider
from agents.cloud.cloud_ecology_agent import CloudEcologyAgent


class TestOfflineProviders(unittest.TestCase):
    def test_weather_provider_returns_local_snapshot(self):
        snapshot = OfflineWeatherProvider().get_weather("121.48, 31.23")

        self.assertEqual(snapshot.city, "上海")
        self.assertIn("晴", snapshot.summary)

    def test_charge_provider_returns_nearest_station(self):
        stations = OfflineChargeProvider().find_nearby("121.48, 31.23")

        self.assertGreaterEqual(len(stations), 2)
        self.assertEqual(stations[0].name, "蔚来换电站 上海中心")
        self.assertLessEqual(stations[0].distance_km, stations[1].distance_km)

    def test_ecology_agent_combines_offline_provider_data(self):
        agent = CloudEcologyAgent()

        result = agent.get_data("121.48, 31.23")
        snapshot = agent.get_snapshot("121.48, 31.23")

        self.assertIn("天气晴", result)
        self.assertIn("蔚来换电站 上海中心", result)
        self.assertEqual(snapshot["weather"]["city"], "上海")
        self.assertEqual(snapshot["charge_stations"][0]["status"], "空闲")


if __name__ == "__main__":
    unittest.main()
