from enum import Enum


class StrEnum(str, Enum):
    def __str__(self):
        return self.value


class CommandType(StrEnum):
    NAVIGATION = "NAVIGATION"
    CAR_CONTROL = "CAR_CONTROL"
    CHARGE_PLAN = "CHARGE_PLAN"
    PERSONALIZE = "PERSONALIZE"
    INFO_QUERY = "INFO_QUERY"
    UNKNOWN = "UNKNOWN"


class SafetyLevel(StrEnum):
    SAFE = "SAFE"
    DANGEROUS = "DANGEROUS"


class NetworkStatus(StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class ExecutionStatus(StrEnum):
    EXECUTED = "EXECUTED"
    BLOCKED = "BLOCKED"
    FALLBACK = "FALLBACK"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NEEDS_DRIVER_CONFIRMATION = "NEEDS_DRIVER_CONFIRMATION"


class RoadType(StrEnum):
    URBAN = "URBAN"
    HIGHWAY = "HIGHWAY"
    UNKNOWN = "UNKNOWN"


class DriverAssistMode(StrEnum):
    MANUAL = "MANUAL"
    ACC = "ACC"
    NOA = "NOA"
