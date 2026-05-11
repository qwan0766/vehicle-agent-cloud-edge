from typing import Optional


class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        operation: str,
        code: str = "PROVIDER_ERROR",
        retryable: bool = False,
        details: Optional[dict] = None,
    ):
        self.provider = provider
        self.operation = operation
        self.code = code
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)

    def to_dict(self):
        return {
            "provider": self.provider,
            "operation": self.operation,
            "code": self.code,
            "retryable": self.retryable,
            "message": str(self),
            "details": self.details,
        }


class ProviderTimeoutError(ProviderError):
    def __init__(self, message: str, *, provider: str, operation: str, details: Optional[dict] = None):
        super().__init__(
            message,
            provider=provider,
            operation=operation,
            code="PROVIDER_TIMEOUT",
            retryable=True,
            details=details,
        )


class ProviderUnavailableError(ProviderError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        operation: str,
        code: str = "PROVIDER_UNAVAILABLE",
        details: Optional[dict] = None,
    ):
        super().__init__(
            message,
            provider=provider,
            operation=operation,
            code=code,
            retryable=True,
            details=details,
        )


class ProviderBadResponseError(ProviderError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        operation: str,
        code: str = "PROVIDER_BAD_RESPONSE",
        details: Optional[dict] = None,
    ):
        super().__init__(
            message,
            provider=provider,
            operation=operation,
            code=code,
            retryable=False,
            details=details,
        )
