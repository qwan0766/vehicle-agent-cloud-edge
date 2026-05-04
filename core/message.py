from dataclasses import dataclass
import uuid

from core.constants import CommandType, NetworkStatus, SafetyLevel


@dataclass(frozen=True)
class Message:
    request_id: str
    user_id: str
    command_type: CommandType
    safety: SafetyLevel
    content: str
    network: NetworkStatus

    @classmethod
    def create(
        cls,
        user_id: str,
        command_type: CommandType,
        safety: SafetyLevel,
        content: str,
        network: NetworkStatus,
    ):
        return cls(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            command_type=command_type,
            safety=safety,
            content=content,
            network=network,
        )
