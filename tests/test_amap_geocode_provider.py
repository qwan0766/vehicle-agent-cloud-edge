import unittest

from providers.amap_geocode_provider import AmapGeocodeProvider


class TestAmapGeocodeProvider(unittest.TestCase):
    def test_builds_geocode_url_with_inferred_city_for_ambiguous_shanghai_landmark(self):
        provider = AmapGeocodeProvider(api_key="amap-key")

        url = provider.build_geocode_url("外滩")

        self.assertIn("https://restapi.amap.com/v3/geocode/geo", url)
        self.assertIn("key=amap-key", url)
        self.assertIn("address=%E5%A4%96%E6%BB%A9", url)
        self.assertIn("city=%E4%B8%8A%E6%B5%B7", url)

    def test_builds_geocode_url_with_inferred_city_for_xiaoshan_airport(self):
        provider = AmapGeocodeProvider(api_key="amap-key")

        url = provider.build_geocode_url("萧山机场")

        self.assertIn("city=%E6%9D%AD%E5%B7%9E", url)

    def test_builds_geocode_url_without_city_when_no_city_hint_exists(self):
        provider = AmapGeocodeProvider(api_key="amap-key")

        url = provider.build_geocode_url("巴黎")

        self.assertNotIn("city=", url)

    def test_builds_geocode_url_with_optional_city(self):
        provider = AmapGeocodeProvider(api_key="amap-key", city="上海")

        url = provider.build_geocode_url("外滩")

        self.assertIn("city=%E4%B8%8A%E6%B5%B7", url)

    def test_parses_geocode_result(self):
        payload = {
            "status": "1",
            "geocodes": [
                {
                    "formatted_address": "上海市黄浦区外滩",
                    "location": "121.490317,31.237972",
                }
            ],
        }
        provider = AmapGeocodeProvider(
            api_key="amap-key",
            transport=lambda url, timeout: payload,
        )

        result = provider.geocode("外滩")

        self.assertEqual(result.name, "外滩")
        self.assertEqual(result.gps, "121.490317,31.237972")
        self.assertEqual(result.formatted_address, "上海市黄浦区外滩")


if __name__ == "__main__":
    unittest.main()
