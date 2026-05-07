from dataclasses import dataclass
from typing import Dict, List

from core.constants import CommandType


@dataclass(frozen=True)
class IntentFrame:
    command_type: CommandType
    slots: Dict[str, object]
    confidence: float
    evidence: Dict[str, object]
    risk_signals: List[str]
    reason: str
