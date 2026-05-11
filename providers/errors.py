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
        user_message: str = "",
    ):
        self.provider = provider
        self.operation = operation
        self.code = code
        self.retryable = retryable
        self.details = details or {}
        self.user_message = user_message or _default_user_message(provider, retryable)
        super().__init__(message)

    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "provider": self.provider,
            "operation": self.operation,
            "code": self.code,
            "error_code": self.code,
            "retryable": self.retryable,
            "message": str(self),
            "user_message": self.user_message,
            "technical_detail": str(self),
            "details": self.details,
            "status": "ERROR",
        }

    def to_payload(self):
        return self.to_dict()


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


def coerce_provider_error(
    exc: Exception,
    *,
    provider: str = "unknown_provider",
    operation: str = "unknown_operation",
) -> ProviderError:
    if isinstance(exc, ProviderError):
        return exc
    if isinstance(exc, TimeoutError):
        return ProviderTimeoutError(
            "Provider request timed out",
            provider=provider,
            operation=operation,
            details={"original_type": exc.__class__.__name__},
        )
    return ProviderError(
        "Provider call failed",
        provider=provider,
        operation=operation,
        code=exc.__class__.__name__,
        retryable=False,
        details={"original_type": exc.__class__.__name__},
        user_message="外部服务调用失败，请稍后重试或检查 Provider 状态。",
    )


def _default_user_message(provider: str, retryable: bool) -> str:
    if retryable:
        return f"{provider} 暂时不可用，请稍后重试。"
    return f"{provider} 返回的数据无法被系统可靠使用，请检查输入或 Provider 响应。"
