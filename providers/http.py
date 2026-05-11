import json
from socket import timeout as SocketTimeout
import time
from typing import Dict, Optional
from urllib import error, request

from providers.errors import (
    ProviderBadResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from providers.runtime import get_default_provider_runtime


def get_json(
    url: str,
    timeout: int,
    *,
    provider: str,
    operation: str,
    headers: Optional[Dict[str, str]] = None,
    retries: Optional[int] = None,
    backoff_seconds: Optional[float] = None,
    runtime=None,
):
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "weilai-agent-online-demo/1.0",
    }
    request_headers.update(headers or {})

    runtime = runtime or get_default_provider_runtime()
    retries = runtime.config.retries if retries is None else retries
    backoff_seconds = (
        runtime.config.backoff_seconds if backoff_seconds is None else backoff_seconds
    )
    runtime.before_call(provider, operation)

    started_at = time.perf_counter()
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = request.Request(url, headers=request_headers, method="GET")
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            payload = json.loads(raw)
            runtime.record_success(
                provider,
                operation,
                latency_ms=_elapsed_ms(started_at),
            )
            return payload
        except TimeoutError as exc:
            last_error = ProviderTimeoutError(
                "Provider request timed out",
                provider=provider,
                operation=operation,
                details={"url": _safe_url(url), "attempt": attempt + 1},
            )
        except SocketTimeout as exc:
            last_error = ProviderTimeoutError(
                "Provider request timed out",
                provider=provider,
                operation=operation,
                details={"url": _safe_url(url), "attempt": attempt + 1},
            )
        except error.HTTPError as exc:
            retryable = exc.code >= 500 or exc.code == 429
            if retryable:
                last_error = ProviderUnavailableError(
                    f"Provider HTTP error: {exc.code}",
                    provider=provider,
                    operation=operation,
                    code=f"HTTP_{exc.code}",
                    details={"url": _safe_url(url), "attempt": attempt + 1},
                )
            else:
                provider_error = ProviderBadResponseError(
                    f"Provider HTTP error: {exc.code}",
                    provider=provider,
                    operation=operation,
                    code=f"HTTP_{exc.code}",
                    details={"url": _safe_url(url), "attempt": attempt + 1},
                )
                runtime.record_failure(
                    provider,
                    operation,
                    provider_error,
                    latency_ms=_elapsed_ms(started_at),
                )
                raise provider_error from exc
        except error.URLError as exc:
            last_error = ProviderUnavailableError(
                "Provider network error",
                provider=provider,
                operation=operation,
                details={
                    "url": _safe_url(url),
                    "attempt": attempt + 1,
                    "reason": str(exc.reason),
                },
            )
        except json.JSONDecodeError as exc:
            provider_error = ProviderBadResponseError(
                "Provider returned invalid JSON",
                provider=provider,
                operation=operation,
                code="INVALID_JSON",
                details={"url": _safe_url(url), "attempt": attempt + 1},
            )
            runtime.record_failure(
                provider,
                operation,
                provider_error,
                latency_ms=_elapsed_ms(started_at),
            )
            raise provider_error from exc

        if attempt < retries:
            time.sleep(backoff_seconds * (attempt + 1))

    runtime.record_failure(
        provider,
        operation,
        last_error,
        latency_ms=_elapsed_ms(started_at),
    )
    raise last_error


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


def _safe_url(url: str) -> str:
    if "key=" not in url and "ak=" not in url:
        return url
    for token in ("key=", "ak="):
        if token in url:
            prefix, suffix = url.split(token, 1)
            if "&" in suffix:
                _secret, rest = suffix.split("&", 1)
                return f"{prefix}{token}***&{rest}"
            return f"{prefix}{token}***"
    return url
