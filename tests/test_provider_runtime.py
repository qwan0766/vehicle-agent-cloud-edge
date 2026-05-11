import unittest
from urllib import error
from unittest.mock import patch

from providers.errors import ProviderCircuitOpenError, ProviderUnavailableError
from providers.http import get_json
from providers.runtime import (
    HEALTH_DEGRADED,
    HEALTH_OK,
    HEALTH_OPEN,
    ProviderRuntime,
    ProviderRuntimeConfig,
)


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds: float):
        self.now += seconds


class TestProviderRuntime(unittest.TestCase):
    def test_retryable_failures_open_circuit_and_block_next_call(self):
        clock = FakeClock()
        runtime = ProviderRuntime(
            ProviderRuntimeConfig(circuit_failure_threshold=2, circuit_reset_seconds=30),
            clock=clock,
        )
        error_one = ProviderUnavailableError(
            "temporary",
            provider="amap_route",
            operation="driving_route",
        )
        error_two = ProviderUnavailableError(
            "temporary",
            provider="amap_route",
            operation="driving_route",
        )

        runtime.record_failure("amap_route", "driving_route", error_one)
        self.assertEqual(runtime.health("amap_route", "driving_route").status, HEALTH_DEGRADED)

        runtime.record_failure("amap_route", "driving_route", error_two)

        snapshot = runtime.health("amap_route", "driving_route")
        self.assertEqual(snapshot.status, HEALTH_OPEN)
        self.assertEqual(snapshot.failure_count, 2)
        with self.assertRaises(ProviderCircuitOpenError):
            runtime.before_call("amap_route", "driving_route")

    def test_circuit_allows_probe_after_reset_window_and_success_resets_health(self):
        clock = FakeClock()
        runtime = ProviderRuntime(
            ProviderRuntimeConfig(circuit_failure_threshold=1, circuit_reset_seconds=5),
            clock=clock,
        )
        runtime.record_failure(
            "open_meteo",
            "forecast",
            ProviderUnavailableError(
                "temporary",
                provider="open_meteo",
                operation="forecast",
            ),
        )
        clock.advance(6)

        runtime.before_call("open_meteo", "forecast")
        runtime.record_success("open_meteo", "forecast", latency_ms=12.3)

        snapshot = runtime.health("open_meteo", "forecast")
        self.assertEqual(snapshot.status, HEALTH_OK)
        self.assertEqual(snapshot.failure_count, 0)
        self.assertEqual(snapshot.last_latency_ms, 12.3)

    def test_get_json_records_success_health(self):
        runtime = ProviderRuntime()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"status":"1"}'

        with patch("providers.http.request.urlopen", return_value=FakeResponse()):
            payload = get_json(
                "https://example.test",
                1,
                provider="demo",
                operation="fetch",
                runtime=runtime,
            )

        self.assertEqual(payload, {"status": "1"})
        self.assertEqual(runtime.health("demo", "fetch").status, HEALTH_OK)

    def test_get_json_records_retryable_failure_and_opens_circuit(self):
        runtime = ProviderRuntime(
            ProviderRuntimeConfig(circuit_failure_threshold=1),
        )
        http_error = error.HTTPError(
            url="https://example.test?key=secret",
            code=500,
            msg="server error",
            hdrs=None,
            fp=None,
        )

        with patch("providers.http.request.urlopen", side_effect=http_error):
            with self.assertRaises(ProviderUnavailableError):
                get_json(
                    "https://example.test?key=secret",
                    1,
                    provider="demo",
                    operation="fetch",
                    retries=0,
                    runtime=runtime,
                )

        snapshot = runtime.health("demo", "fetch")
        self.assertEqual(snapshot.status, HEALTH_OPEN)
        self.assertEqual(snapshot.last_error_code, "HTTP_500")

    def test_get_json_uses_runtime_retry_and_backoff_defaults(self):
        runtime = ProviderRuntime(
            ProviderRuntimeConfig(retries=2, backoff_seconds=0),
        )

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok":true}'

        http_error = error.HTTPError(
            url="https://example.test",
            code=500,
            msg="server error",
            hdrs=None,
            fp=None,
        )
        calls = [http_error, http_error, FakeResponse()]

        def fake_urlopen(_req, timeout):
            result = calls.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with patch("providers.http.request.urlopen", side_effect=fake_urlopen):
            payload = get_json(
                "https://example.test",
                1,
                provider="demo",
                operation="fetch",
                runtime=runtime,
            )

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(runtime.health("demo", "fetch").status, HEALTH_OK)


if __name__ == "__main__":
    unittest.main()
