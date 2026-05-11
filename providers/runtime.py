from dataclasses import dataclass, field
from time import monotonic
from typing import Dict, Tuple

from providers.errors import ProviderCircuitOpenError, ProviderError


HEALTH_UNKNOWN = "UNKNOWN"
HEALTH_OK = "OK"
HEALTH_DEGRADED = "DEGRADED"
HEALTH_OPEN = "OPEN"
HEALTH_ERROR = "ERROR"


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    timeout_seconds: int = 10
    retries: int = 1
    backoff_seconds: float = 0.1
    circuit_failure_threshold: int = 3
    circuit_reset_seconds: float = 30.0
    health_ttl_seconds: float = 30.0

    def __post_init__(self):
        object.__setattr__(self, "timeout_seconds", max(1, int(self.timeout_seconds)))
        object.__setattr__(self, "retries", max(0, int(self.retries)))
        object.__setattr__(self, "backoff_seconds", max(0.0, float(self.backoff_seconds)))
        object.__setattr__(
            self,
            "circuit_failure_threshold",
            max(1, int(self.circuit_failure_threshold)),
        )
        object.__setattr__(
            self,
            "circuit_reset_seconds",
            max(0.0, float(self.circuit_reset_seconds)),
        )
        object.__setattr__(
            self,
            "health_ttl_seconds",
            max(0.0, float(self.health_ttl_seconds)),
        )


@dataclass
class ProviderHealthSnapshot:
    provider: str
    operation: str
    status: str = HEALTH_UNKNOWN
    failure_count: int = 0
    last_error_code: str = ""
    last_latency_ms: float = 0.0
    updated_at: float = field(default_factory=monotonic)
    opened_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "operation": self.operation,
            "status": self.status,
            "failure_count": self.failure_count,
            "last_error_code": self.last_error_code,
            "last_latency_ms": self.last_latency_ms,
            "updated_at": self.updated_at,
            "opened_at": self.opened_at,
        }


class ProviderRuntime:
    def __init__(self, config: ProviderRuntimeConfig = None, clock=monotonic):
        self.config = config or ProviderRuntimeConfig()
        self.clock = clock
        self._health: Dict[Tuple[str, str], ProviderHealthSnapshot] = {}

    def before_call(self, provider: str, operation: str):
        snapshot = self._snapshot(provider, operation)
        if snapshot.status != HEALTH_OPEN:
            return
        elapsed = self.clock() - snapshot.opened_at
        if elapsed >= self.config.circuit_reset_seconds:
            snapshot.status = HEALTH_DEGRADED
            snapshot.failure_count = max(0, snapshot.failure_count - 1)
            snapshot.updated_at = self.clock()
            return
        raise ProviderCircuitOpenError(
            "Provider circuit is open",
            provider=provider,
            operation=operation,
            details={
                "failure_count": snapshot.failure_count,
                "reset_after_seconds": round(
                    self.config.circuit_reset_seconds - elapsed,
                    3,
                ),
            },
        )

    def record_success(self, provider: str, operation: str, latency_ms: float = 0.0):
        snapshot = self._snapshot(provider, operation)
        snapshot.status = HEALTH_OK
        snapshot.failure_count = 0
        snapshot.last_error_code = ""
        snapshot.last_latency_ms = float(latency_ms)
        snapshot.updated_at = self.clock()
        snapshot.opened_at = 0.0

    def record_failure(
        self,
        provider: str,
        operation: str,
        error: Exception,
        latency_ms: float = 0.0,
    ):
        snapshot = self._snapshot(provider, operation)
        retryable = bool(getattr(error, "retryable", False))
        snapshot.failure_count = snapshot.failure_count + 1 if retryable else 0
        snapshot.last_error_code = str(getattr(error, "code", error.__class__.__name__))
        snapshot.last_latency_ms = float(latency_ms)
        snapshot.updated_at = self.clock()
        if retryable and snapshot.failure_count >= self.config.circuit_failure_threshold:
            snapshot.status = HEALTH_OPEN
            snapshot.opened_at = self.clock()
        else:
            snapshot.status = HEALTH_DEGRADED if retryable else HEALTH_ERROR

    def health(self, provider: str, operation: str = "") -> ProviderHealthSnapshot:
        if operation:
            return self._health_snapshot(provider, operation)
        snapshots = [
            item
            for (name, _operation), item in self._health.items()
            if name == provider and not self._is_expired(item)
        ]
        if not snapshots:
            return ProviderHealthSnapshot(provider=provider, operation="")
        if any(item.status == HEALTH_OPEN for item in snapshots):
            status = HEALTH_OPEN
        elif any(item.status in {HEALTH_DEGRADED, HEALTH_ERROR} for item in snapshots):
            status = HEALTH_DEGRADED
        else:
            status = HEALTH_OK
        newest = max(snapshots, key=lambda item: item.updated_at)
        return ProviderHealthSnapshot(
            provider=provider,
            operation="*",
            status=status,
            failure_count=sum(item.failure_count for item in snapshots),
            last_error_code=newest.last_error_code,
            last_latency_ms=newest.last_latency_ms,
            updated_at=newest.updated_at,
            opened_at=newest.opened_at,
        )

    def all_health(self):
        return [
            snapshot.to_dict()
            for snapshot in self._health.values()
            if not self._is_expired(snapshot)
        ]

    def reset(self):
        self._health.clear()

    def _snapshot(self, provider: str, operation: str) -> ProviderHealthSnapshot:
        key = (provider, operation)
        if key not in self._health:
            self._health[key] = ProviderHealthSnapshot(
                provider=provider,
                operation=operation,
            )
        return self._health[key]

    def _health_snapshot(self, provider: str, operation: str) -> ProviderHealthSnapshot:
        key = (provider, operation)
        snapshot = self._health.get(key)
        if snapshot is None:
            return ProviderHealthSnapshot(provider=provider, operation=operation)
        if self._is_expired(snapshot):
            self._health.pop(key, None)
            return ProviderHealthSnapshot(provider=provider, operation=operation)
        return snapshot

    def _is_expired(self, snapshot: ProviderHealthSnapshot) -> bool:
        ttl = self.config.health_ttl_seconds
        if ttl <= 0 or snapshot.status == HEALTH_OPEN:
            return False
        return self.clock() - snapshot.updated_at > ttl


_DEFAULT_RUNTIME = None


def get_default_provider_runtime() -> ProviderRuntime:
    global _DEFAULT_RUNTIME
    if _DEFAULT_RUNTIME is None:
        from config.settings import get_settings

        _DEFAULT_RUNTIME = ProviderRuntime(get_settings().provider_runtime)
    return _DEFAULT_RUNTIME


def reset_default_provider_runtime(runtime: ProviderRuntime = None):
    global _DEFAULT_RUNTIME
    _DEFAULT_RUNTIME = runtime
