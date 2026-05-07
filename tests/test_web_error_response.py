import unittest

from web_demo.server import build_error_response


class TestWebErrorResponse(unittest.TestCase):
    def test_maps_amap_geocode_error_to_user_friendly_message(self):
        payload = build_error_response(
            RuntimeError("AMap geocode error: ENGINE_RESPONSE_DATA_ERROR"),
            content="导航去巴黎",
            network="ONLINE",
        )

        self.assertEqual(payload["provider"], "amap_geocode")
        self.assertEqual(payload["user_title"], "没有找到这个目的地")
        self.assertIn("巴黎", payload["user_message"])
        self.assertTrue(payload["suggestions"])
        self.assertIn("technical_message", payload)

    def test_maps_timeout_to_retry_guidance(self):
        payload = build_error_response(TimeoutError("request timed out"))

        self.assertEqual(payload["user_title"], "外部服务响应超时")
        self.assertTrue(any("Smoke Test" in item for item in payload["suggestions"]))

    def test_maps_low_confidence_geocode_to_clarification_guidance(self):
        payload = build_error_response(
            RuntimeError(
                "AMap geocode low confidence: query=霓虹蔚来中心, "
                "formatted_address=上海市松江区蔚来中心(上海松江印象城)"
            ),
            content="导航去霓虹蔚来中心",
            network="ONLINE",
        )

        self.assertEqual(payload["provider"], "amap_geocode")
        self.assertEqual(payload["user_title"], "目的地置信度过低")
        self.assertIn("没有直接开始导航", payload["user_message"])
        self.assertIn("霓虹蔚来中心", payload["user_message"])


if __name__ == "__main__":
    unittest.main()
