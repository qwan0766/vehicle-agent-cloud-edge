from pathlib import Path
import uuid

from core.constants import CommandType, ExecutionStatus, NetworkStatus
from core.vehicle_core_service import VehicleCoreService
from memory.pending_clarification_store import PendingClarificationStore
from providers.destination_resolver import DestinationClarificationRequired


def _pending_test_path():
    path = Path(".tmp-tests") / f"pending-{uuid.uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class FailingCloudAgent:
    def dispatch(self, msg):
        raise AssertionError("cloud should not run before clarification")

    def get_last_trace(self):
        return []

    def get_last_graph(self):
        return {}


class RecordingCloudAgent:
    def __init__(self):
        self.contents = []

    def dispatch(self, msg):
        self.contents.append(msg.content)
        return "route ok"

    def get_last_trace(self):
        return []

    def get_last_graph(self):
        return {}


def test_execution_status_has_needs_clarification():
    assert ExecutionStatus.NEEDS_CLARIFICATION.value == "NEEDS_CLARIFICATION"


def test_build_destination_clarification_payload():
    from core.clarification import build_destination_clarification

    exc = DestinationClarificationRequired(
        query="北京",
        reason="broad_region",
        suggestions=["导航去北京东方广场蔚来中心"],
    )

    payload = build_destination_clarification(exc, original_content="导航去北京")

    assert payload["type"] == "destination"
    assert payload["query"] == "北京"
    assert payload["reason"] == "broad_region"
    assert payload["original_content"] == "导航去北京"
    assert payload["suggestions"] == ["导航去北京东方广场蔚来中心"]
    assert payload["candidates"] == []
    assert "具体" in payload["question"]


def test_build_destination_clarification_explains_uncertain_chain_store():
    from core.clarification import build_destination_clarification

    exc = DestinationClarificationRequired(
        query="霓虹蔚来中心",
        reason="unknown_chain_poi_qualifier",
    )

    payload = build_destination_clarification(exc, original_content="导航去霓虹蔚来中心")

    assert payload["query"] == "霓虹蔚来中心"
    assert payload["suggestions"]
    assert "门店" in payload["question"]


def test_build_destination_clarification_includes_low_confidence_candidates():
    from core.clarification import build_destination_clarification

    candidate = {
        "name": "北京东方未来中心",
        "gps": "116.417,39.915",
        "address": "北京市东城区东方广场",
        "source": "fake_geocode",
        "confidence": 0.35,
        "distance_km": None,
        "reason": "missing_significant_terms:蔚来中心",
    }
    exc = DestinationClarificationRequired(
        query="北京东方广场蔚来中心",
        reason="low_confidence_provider_result",
        candidates=[candidate],
    )

    payload = build_destination_clarification(
        exc,
        original_content="导航去北京东方广场蔚来中心",
    )

    assert payload["reason"] == "low_confidence_provider_result"
    assert payload["candidates"] == [candidate]
    assert "置信度" in payload["question"]


def test_destination_refinement_reconstructs_original_navigation_intent():
    from core.clarification import (
        is_destination_refinement,
        reconstruct_destination_command,
    )

    pending = {
        "type": "destination",
        "query": "北京",
        "original_content": "导航去北京",
    }

    assert is_destination_refinement("东方广场蔚来中心", pending) is True
    assert (
        reconstruct_destination_command("东方广场蔚来中心", pending)
        == "导航去北京东方广场蔚来中心"
    )


def test_destination_refinement_ignores_new_or_dangerous_commands():
    from core.clarification import is_destination_refinement

    pending = {
        "type": "destination",
        "query": "北京",
        "original_content": "导航去北京",
    }

    assert is_destination_refinement("导航去上海外滩", pending) is False
    assert is_destination_refinement("温度调到24度", pending) is False
    assert is_destination_refinement("关闭AEB", pending) is False


def test_pending_clarification_store_is_user_scoped():
    from memory.pending_clarification_store import PendingClarificationStore

    store = PendingClarificationStore(_pending_test_path())
    store.save("user_001", "default", {"type": "destination", "query": "北京"})

    assert store.get("user_001", "default")["query"] == "北京"
    assert store.get("user_002", "default") is None


def test_pending_clarification_store_clears_only_matching_scope():
    from memory.pending_clarification_store import PendingClarificationStore

    store = PendingClarificationStore(_pending_test_path())
    store.save("user_001", "default", {"type": "destination", "query": "北京"})
    store.save("user_001", "session_2", {"type": "destination", "query": "上海"})

    store.clear("user_001", "default")

    assert store.get("user_001", "default") is None
    assert store.get("user_001", "session_2")["query"] == "上海"


def test_pending_clarification_store_ignores_invalid_file():
    path = _pending_test_path()
    path.write_text("{", encoding="utf-8")
    store = PendingClarificationStore(path)

    assert store.get("user_001", "default") is None


def test_ambiguous_navigation_returns_clarification_before_cloud_dispatch():
    store = PendingClarificationStore(_pending_test_path())
    service = VehicleCoreService(
        cloud_agent=FailingCloudAgent(),
        pending_clarification_store=store,
    )

    result = service.run("导航去北京", network=NetworkStatus.ONLINE)

    assert result.status == ExecutionStatus.NEEDS_CLARIFICATION
    assert result.message.command_type == CommandType.NAVIGATION
    assert result.clarification["type"] == "destination"
    assert result.clarification["query"] == "北京"
    assert store.get("user_001", "default")["query"] == "北京"


def test_unclear_and_unknown_chain_destinations_need_clarification():
    for content, query, reason in [
        ("导航去高老庄", "高老庄", "unclear_destination"),
        ("导航去霓虹蔚来中心", "霓虹蔚来中心", "unknown_chain_poi_qualifier"),
    ]:
        store = PendingClarificationStore(_pending_test_path())
        service = VehicleCoreService(
            cloud_agent=FailingCloudAgent(),
            pending_clarification_store=store,
        )

        result = service.run(content, network=NetworkStatus.ONLINE)

        assert result.status == ExecutionStatus.NEEDS_CLARIFICATION
        assert result.clarification["query"] == query
        assert result.clarification["reason"] == reason


def test_follow_up_destination_fragment_resumes_pending_navigation():
    store = PendingClarificationStore(_pending_test_path())
    cloud = RecordingCloudAgent()
    service = VehicleCoreService(
        cloud_agent=cloud,
        pending_clarification_store=store,
    )

    first = service.run("导航去北京", network=NetworkStatus.ONLINE)
    second = service.run("东方广场蔚来中心", network=NetworkStatus.ONLINE)

    assert first.status == ExecutionStatus.NEEDS_CLARIFICATION
    assert second.status == ExecutionStatus.EXECUTED
    assert cloud.contents == ["导航去北京东方广场蔚来中心"]
    assert store.get("user_001", "default") is None


def test_complete_new_command_does_not_reuse_pending_destination():
    store = PendingClarificationStore(_pending_test_path())
    cloud = RecordingCloudAgent()
    service = VehicleCoreService(
        cloud_agent=cloud,
        pending_clarification_store=store,
    )

    service.run("导航去北京", network=NetworkStatus.ONLINE)
    result = service.run("导航去上海外滩", network=NetworkStatus.ONLINE)

    assert result.status == ExecutionStatus.EXECUTED
    assert cloud.contents == ["导航去上海外滩"]
    assert store.get("user_001", "default") is None


def test_non_navigation_follow_up_clears_pending_destination():
    store = PendingClarificationStore(_pending_test_path())
    cloud = RecordingCloudAgent()
    service = VehicleCoreService(
        cloud_agent=cloud,
        pending_clarification_store=store,
    )

    service.run("导航去北京", network=NetworkStatus.ONLINE)
    result = service.run("温度调到24度", network=NetworkStatus.ONLINE)

    assert result.status == ExecutionStatus.EXECUTED
    assert cloud.contents == ["温度调到24度"]
    assert store.get("user_001", "default") is None


def test_dangerous_follow_up_is_blocked_without_destination_reconstruction():
    store = PendingClarificationStore(_pending_test_path())
    cloud = RecordingCloudAgent()
    service = VehicleCoreService(
        cloud_agent=cloud,
        pending_clarification_store=store,
    )

    service.run("导航去北京", network=NetworkStatus.ONLINE)
    result = service.run("关闭AEB", network=NetworkStatus.ONLINE)

    assert result.status == ExecutionStatus.BLOCKED
    assert cloud.contents == []
    assert store.get("user_001", "default") is None
