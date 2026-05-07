from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class DestinationCandidate:
    name: str
    gps: str = ""
    address: str = ""
    source: str = ""
    confidence: float = 0.0
    distance_km: Optional[float] = None
    reason: str = ""

    def to_payload(self) -> dict:
        return {
            "name": self.name,
            "gps": self.gps,
            "address": self.address,
            "source": self.source,
            "confidence": self.confidence,
            "distance_km": self.distance_km,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DestinationResolution:
    name: str
    gps: str
    source: str
    confidence: float = 1.0
    candidates: Tuple[DestinationCandidate, ...] = ()


@dataclass(frozen=True)
class DestinationClarification:
    query: str
    reason: str
    suggestions: Tuple[str, ...] = ()
    candidates: Tuple[DestinationCandidate, ...] = ()
