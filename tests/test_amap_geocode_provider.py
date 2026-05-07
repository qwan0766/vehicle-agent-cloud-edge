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

    def test_builds_geocode_url_with_explicit_beijing_before_nio_center_hint(self):
        provider = AmapGeocodeProvider(api_key="amap-key")

        url = provider.build_geocode_url("北京蔚来中心")

        self.assertIn("address=%E5%8C%97%E4%BA%AC%E8%94%9A%E6%9D%A5%E4%B8%AD%E5%BF%83", url)
        self.assertIn("city=%E5%8C%97%E4%BA%AC", url)
        self.assertNotIn("city=%E4%B8%8A%E6%B5%B7", url)

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

    def test_rejects_low_confidence_fuzzy_nio_center_match(self):
        payload = {
            "status": "1",
            "geocodes": [
                {
                    "formatted_address": "上海市松江区蔚来中心(上海松江印象城)",
                    "location": "121.222719,31.062206",
                    "level": "兴趣点",
                }
            ],
        }
        provider = AmapGeocodeProvider(
            api_key="amap-key",
            transport=lambda url, timeout: payload,
        )

        with self.assertRaisesRegex(RuntimeError, "low confidence"):
            provider.geocode("霓虹蔚来中心")

    def test_accepts_city_qualified_nio_center_when_terms_match(self):
        payload = {
            "status": "1",
            "geocodes": [
                {
                    "formatted_address": "北京市东城区蔚来中心(北京东方广场)",
                    "location": "116.416954,39.909126",
                    "level": "兴趣点",
                }
            ],
        }
        provider = AmapGeocodeProvider(
            api_key="amap-key",
            transport=lambda url, timeout: payload,
        )

        result = provider.geocode("北京蔚来中心")

        self.assertEqual(result.name, "北京蔚来中心")
        self.assertEqual(result.gps, "116.416954,39.909126")
        self.assertGreaterEqual(result.confidence, 0.8)
        self.assertEqual(result.quality_reason, "matched_significant_terms")


if __name__ == "__main__":
    unittest.main()
