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


def get_json(
    url: str,
    timeout: int,
    *,
    provider: str,
    operation: str,
    headers: Optional[Dict[str, str]] = None,
    retries: int = 1,
):
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "weilai-agent-online-demo/1.0",
    }
    request_headers.update(headers or {})

    last_error = None
    for attempt in range(retries + 1):
        try:
            req = request.Request(url, headers=request_headers, method="GET")
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            return json.loads(raw)
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
                raise ProviderBadResponseError(
                    f"Provider HTTP error: {exc.code}",
                    provider=provider,
                    operation=operation,
                    code=f"HTTP_{exc.code}",
                    details={"url": _safe_url(url), "attempt": attempt + 1},
                ) from exc
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
            raise ProviderBadResponseError(
                "Provider returned invalid JSON",
                provider=provider,
                operation=operation,
                code="INVALID_JSON",
                details={"url": _safe_url(url), "attempt": attempt + 1},
            ) from exc

        if attempt < retries:
            time.sleep(0.1 * (attempt + 1))

    raise last_error


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
