from providers.destination_clarification_policy import ClarificationPolicy
from providers.destination_models import (
    DestinationCandidate,
    DestinationClarification,
    DestinationResolution,
)
from providers.destination_query import (
    NAVIGATION_PREFIXES,
    extract_destination_query,
    looks_like_gps,
    normalize_destination_query,
)
from providers.destination_service import (
    DestinationClarificationRequired,
    DestinationResolver,
    KNOWN_DESTINATIONS,
)


def resolve_destination(content: str, geocoder=None) -> str:
    return resolve_destination_detail(content, geocoder=geocoder).gps


def resolve_destination_detail(content: str, geocoder=None) -> DestinationResolution:
    return DestinationResolver().resolve(content, geocoder=geocoder)


def assess_destination_clarification(query: str):
    clarification = ClarificationPolicy().assess(
        query,
        known_destinations=KNOWN_DESTINATIONS,
    )
    if not clarification:
        return None
    return DestinationClarificationRequired(
        clarification.query,
        clarification.reason,
        suggestions=clarification.suggestions,
        candidates=[item.to_payload() for item in clarification.candidates],
    )


__all__ = [
    "DestinationCandidate",
    "DestinationClarification",
    "DestinationResolution",
    "DestinationClarificationRequired",
    "DestinationResolver",
    "KNOWN_DESTINATIONS",
    "NAVIGATION_PREFIXES",
    "resolve_destination",
    "resolve_destination_detail",
    "extract_destination_query",
    "normalize_destination_query",
    "assess_destination_clarification",
    "looks_like_gps",
]
