import unittest

from providers.amap_poi_provider import AmapPOIProvider


class TestAmapPOIProvider(unittest.TestCase):
    def test_builds_around_search_url_for_charge_station(self):
        provider = AmapPOIProvider(api_key="amap-key")

        url = provider.build_around_search_url("121.48, 31.23", limit=5)

        self.assertIn("https://restapi.amap.com/v3/place/around", url)
        self.assertIn("key=amap-key", url)
        self.assertIn("location=121.48%2C31.23", url)
        self.assertIn("types=011100", url)
        self.assertIn("offset=5", url)

    def test_parses_pois_into_charge_stations(self):
        payload = {
            "status": "1",
            "pois": [
                {
                    "name": "高德充电站A",
                    "distance": "320",
                    "biz_ext": {},
                }
            ],
        }
        provider = AmapPOIProvider(api_key="amap-key", transport=lambda url, timeout: payload)

        stations = provider.find_nearby("121.48, 31.23", limit=1)

        self.assertEqual(stations[0].name, "高德充电站A")
        self.assertEqual(stations[0].distance_km, 0.32)
        self.assertEqual(stations[0].status, "可用")


if __name__ == "__main__":
    unittest.main()
