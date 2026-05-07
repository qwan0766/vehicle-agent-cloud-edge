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

    def test_builds_text_search_url_for_destination_candidates(self):
        provider = AmapPOIProvider(api_key="amap-key")

        url = provider.build_text_search_url("世博园", city="上海", limit=2)

        self.assertIn("https://restapi.amap.com/v3/place/text", url)
        self.assertIn("keywords=%E4%B8%96%E5%8D%9A%E5%9B%AD", url)
        self.assertIn("city=%E4%B8%8A%E6%B5%B7", url)
        self.assertIn("citylimit=true", url)
        self.assertIn("offset=2", url)

    def test_parses_text_search_pois_into_destination_candidates(self):
        payload = {
            "status": "1",
            "pois": [
                {
                    "name": "上海世博园",
                    "location": "121.50,31.18",
                    "address": "世博大道",
                    "cityname": "上海市",
                }
            ],
        }
        provider = AmapPOIProvider(api_key="amap-key", transport=lambda url, timeout: payload)

        candidates = provider.search_text("世博园", limit=1)

        self.assertEqual(candidates[0].name, "上海世博园")
        self.assertEqual(candidates[0].gps, "121.50,31.18")
        self.assertEqual(candidates[0].source, "amap_poi")
        self.assertGreaterEqual(candidates[0].confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
