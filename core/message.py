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

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "command_type": self.command_type.value,
            "safety": self.safety.value,
            "content": self.content,
            "network": self.network.value,
        }

    def to_intent_frame(
        self,
        raw_input: str = None,
        normalized_input: str = None,
        confidence: float = 1.0,
        source: str = "message",
        slots: dict = None,
    ):
        from core.agent_schema import IntentFrame

        return IntentFrame.from_message(
            self,
            raw_input=raw_input,
            normalized_input=normalized_input,
            confidence=confidence,
            source=source,
            slots=slots,
        )
