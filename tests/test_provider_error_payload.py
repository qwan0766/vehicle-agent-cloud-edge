import unittest

from providers.errors import (
    ProviderBadResponseError,
    ProviderError,
    ProviderTimeoutError,
    coerce_provider_error,
)


class TestProviderErrorPayload(unittest.TestCase):
    def test_provider_error_payload_has_stable_debug_and_user_fields(self):
        exc = ProviderBadResponseError(
            "AMap route returned malformed route",
            provider="amap_route",
            operation="driving_route",
            code="AMAP_ROUTE_MALFORMED",
            details={"field": "route.paths"},
        )

        payload = exc.to_payload()

        self.assertEqual(payload["type"], "ProviderBadResponseError")
        self.assertEqual(payload["provider"], "amap_route")
        self.assertEqual(payload["operation"], "driving_route")
        self.assertEqual(payload["error_code"], "AMAP_ROUTE_MALFORMED")
        self.assertEqual(payload["code"], "AMAP_ROUTE_MALFORMED")
        self.assertFalse(payload["retryable"])
        self.assertEqual(payload["technical_detail"], "AMap route returned malformed route")
        self.assertIn("user_message", payload)
        self.assertEqual(payload["status"], "ERROR")

    def test_timeout_is_coerced_to_retryable_provider_error(self):
        exc = coerce_provider_error(
            TimeoutError("slow provider"),
            provider="open_meteo",
            operation="forecast",
        )

        self.assertIsInstance(exc, ProviderTimeoutError)
        self.assertTrue(exc.retryable)
        self.assertEqual(exc.code, "PROVIDER_TIMEOUT")
        self.assertEqual(exc.provider, "open_meteo")
        self.assertEqual(exc.operation, "forecast")

    def test_generic_exception_is_coerced_without_losing_original_type(self):
        exc = coerce_provider_error(
            ValueError("bad shape"),
            provider="deepseek",
            operation="chat",
        )

        self.assertIsInstance(exc, ProviderError)
        self.assertEqual(exc.code, "ValueError")
        self.assertFalse(exc.retryable)
        self.assertEqual(exc.details["original_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
