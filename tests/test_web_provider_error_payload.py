import unittest

from providers.errors import ProviderUnavailableError
from web_demo.server import build_error_response


class TestWebProviderErrorPayload(unittest.TestCase):
    def test_web_error_response_prefers_structured_provider_error_payload(self):
        payload = build_error_response(
            ProviderUnavailableError(
                "Provider HTTP error: 503",
                provider="open_meteo",
                operation="forecast",
                code="HTTP_503",
            ),
            content="导航去蔚来中心",
            network="ONLINE",
        )

        self.assertEqual(payload["type"], "ProviderUnavailableError")
        self.assertEqual(payload["provider"], "open_meteo")
        self.assertEqual(payload["operation"], "forecast")
        self.assertEqual(payload["error_code"], "HTTP_503")
        self.assertEqual(payload["user_title"], "外部能力暂时不可用")
        self.assertTrue(payload["retryable"])
        self.assertIn("technical_detail", payload)
        self.assertTrue(payload["suggestions"])


if __name__ == "__main__":
    unittest.main()
