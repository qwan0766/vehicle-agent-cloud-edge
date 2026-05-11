import unittest
from urllib import error
from unittest.mock import patch

from providers.amap_route_provider import AmapRouteProvider
from providers.errors import ProviderBadResponseError, ProviderUnavailableError
from providers.http import get_json
from providers.open_meteo_weather_provider import OpenMeteoWeatherProvider


class TestProviderErrors(unittest.TestCase):
    def test_amap_route_status_error_is_normalized(self):
        provider = AmapRouteProvider(
            api_key="amap-key",
            transport=lambda _url, _timeout: {
                "status": "0",
                "info": "INVALID_PARAMS",
                "infocode": "20000",
            },
        )

        with self.assertRaises(ProviderBadResponseError) as ctx:
            provider.plan_route("121.48,31.23", "121.50,31.25")

        self.assertEqual(ctx.exception.provider, "amap_route")
        self.assertEqual(ctx.exception.operation, "driving_route")
        self.assertEqual(ctx.exception.code, "20000")
        self.assertFalse(ctx.exception.retryable)

    def test_amap_route_empty_paths_is_normalized(self):
        provider = AmapRouteProvider(
            api_key="amap-key",
            transport=lambda _url, _timeout: {"status": "1", "route": {"paths": []}},
        )

        with self.assertRaises(ProviderBadResponseError) as ctx:
            provider.plan_route("121.48,31.23", "121.50,31.25")

        self.assertEqual(ctx.exception.code, "AMAP_ROUTE_EMPTY_PATH")

    def test_open_meteo_missing_current_is_normalized(self):
        provider = OpenMeteoWeatherProvider(transport=lambda _url, _timeout: {})

        with self.assertRaises(ProviderBadResponseError) as ctx:
            provider.get_weather("121.48,31.23")

        self.assertEqual(ctx.exception.provider, "open_meteo")
        self.assertEqual(ctx.exception.code, "OPEN_METEO_MISSING_CURRENT")

    def test_http_json_wraps_http_500_as_retryable_provider_error(self):
        http_error = error.HTTPError(
            url="https://example.test?key=secret",
            code=500,
            msg="server error",
            hdrs=None,
            fp=None,
        )

        with patch("providers.http.request.urlopen", side_effect=http_error):
            with self.assertRaises(ProviderUnavailableError) as ctx:
                get_json(
                    "https://example.test?key=secret",
                    1,
                    provider="demo",
                    operation="fetch",
                    retries=0,
                )

        self.assertEqual(ctx.exception.code, "HTTP_500")
        self.assertTrue(ctx.exception.retryable)
        self.assertNotIn("secret", ctx.exception.details["url"])

    def test_http_json_wraps_invalid_json(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"{bad json"

        with patch("providers.http.request.urlopen", return_value=FakeResponse()):
            with self.assertRaises(ProviderBadResponseError) as ctx:
                get_json("https://example.test", 1, provider="demo", operation="fetch")

        self.assertEqual(ctx.exception.code, "INVALID_JSON")


if __name__ == "__main__":
    unittest.main()
