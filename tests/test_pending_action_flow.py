from pathlib import Path
import uuid

from core.constants import ExecutionStatus, NetworkStatus
from core.vehicle_core_service import VehicleCoreService
from memory.pending_action_store import PendingActionStore
from memory.pending_clarification_store import PendingClarificationStore


def _runtime_path(name: str) -> Path:
    path = Path(".tmp-tests") / f"{name}-{uuid.uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class RecordingCloudAgent:
    def __init__(self):
        self.contents = []

    def dispatch(self, msg):
        self.contents.append(msg.content)
        return f"route ok: {msg.content}"

    def get_last_trace(self):
        return []

    def get_last_graph(self):
        return {}


def test_destination_clarification_creates_pending_action_and_confirm_resumes_route():
    pending_actions = PendingActionStore(_runtime_path("pending-action"))
    cloud = RecordingCloudAgent()
    service = VehicleCoreService(
        cloud_agent=cloud,
        pending_clarification_store=PendingClarificationStore(_runtime_path("pending-clarification")),
        pending_action_store=pending_actions,
    )

    first = service.run("导航去北京", network=NetworkStatus.ONLINE)
    action_id = first.pending_action["id"]

    assert first.status == ExecutionStatus.NEEDS_CLARIFICATION
    assert first.pending_action["type"] == "destination_clarification"
    assert pending_actions.get(action_id)["content"] == "导航去北京"

    second = service.confirm_pending_action(
        action_id,
        user_id="user_001",
        selection={"gps": "121.497253,31.238235", "name": "上海外滩"},
    )

    assert second.status == ExecutionStatus.EXECUTED
    assert cloud.contents == ["导航去121.497253,31.238235"]
    assert pending_actions.get(action_id) is None


def test_driver_confirmation_pending_action_executes_after_explicit_confirmation():
    pending_actions = PendingActionStore(_runtime_path("pending-action"))
    cloud = RecordingCloudAgent()
    service = VehicleCoreService(
        cloud_agent=cloud,
        pending_action_store=pending_actions,
    )

    first = service.run("加速到100km/h", network=NetworkStatus.ONLINE)
    action_id = first.pending_action["id"]
    second = service.confirm_pending_action(action_id, user_id="user_001", confirmed=True)

    assert first.status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION
    assert first.pending_action["type"] == "driver_confirmation"
    assert second.status == ExecutionStatus.EXECUTED
    assert "驾驶员确认" in second.output
    assert cloud.contents == []
    assert pending_actions.get(action_id) is None
