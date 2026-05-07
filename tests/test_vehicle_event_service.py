from data.vehicle_event_service import VehicleEventService
from data.vehicle_state_service import VehicleStateService


def test_low_battery_warning_event_is_normalized():
    state_service = VehicleStateService()
    state_service.update({"battery_percent": 18})

    payload = VehicleEventService().snapshot(state_service.current_state())

    assert payload["events"][0]["type"] == "BATTERY_LOW"
    assert payload["events"][0]["severity"] == "WARNING"
    assert payload["events"][0]["status"] == "ACTIVE"
    assert payload["events"][0]["source_agent"] == "VehicleStateMonitorAgent"
    assert payload["events"][0]["recommended_action"] == "建议规划补能点"
    assert payload["vehicle_state"]["battery_percent"] == 18


def test_critical_battery_event_has_higher_severity():
    state_service = VehicleStateService()
    state_service.update({"battery_percent": 8})

    payload = VehicleEventService().snapshot(state_service.current_state())

    assert payload["events"][0]["type"] == "BATTERY_CRITICAL"
    assert payload["events"][0]["severity"] == "CRITICAL"
    assert payload["events"][0]["recommended_action"] == "请优先前往最近补能点"


def test_normal_vehicle_state_returns_empty_events_with_rules():
    state_service = VehicleStateService()

    payload = VehicleEventService().snapshot(state_service.current_state())

    assert payload["events"] == []
    assert payload["event_rules"][0]["type"] == "BATTERY_LOW"
