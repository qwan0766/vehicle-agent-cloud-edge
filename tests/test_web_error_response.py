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


if __name__ == "__main__":
    unittest.main()
