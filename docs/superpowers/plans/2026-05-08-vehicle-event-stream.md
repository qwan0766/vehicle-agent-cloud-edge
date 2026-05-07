# Vehicle Event Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a proactive vehicle state event stream so low battery and similar vehicle events are visible without waiting for user commands.

**Architecture:** `VehicleStateService` remains the mutable in-memory vehicle state store. `VehicleStateMonitorAgent` detects raw state conditions, while a new `VehicleEventService` normalizes them into UI/API events with severity, source, status, and recommended action. The web demo exposes `GET /api/vehicle-events`, and the frontend polls it periodically to keep the vehicle event panel current.

**Tech Stack:** Python standard library HTTP server, existing dataclasses/enums, plain JavaScript polling, pytest.

---

### Task 1: Event Service And Severity Model

**Files:**
- Create: `data/vehicle_event_service.py`
- Modify: `agents/vehicle/vehicle_state_monitor_agent.py`
- Test: `tests/test_vehicle_event_service.py`

- [ ] **Step 1: Write failing tests**

```python
from data.vehicle_event_service import VehicleEventService
from core.constants import NetworkStatus
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
```

- [ ] **Step 2: Run test and verify it fails**

Run: `python -m pytest tests/test_vehicle_event_service.py -q`

Expected: FAIL because `data.vehicle_event_service` does not exist.

- [ ] **Step 3: Implement minimal event service**

Create `VehicleEventService.snapshot(vehicle_state, network=None)` returning vehicle payload, auto event rules, and normalized events. Extend low battery monitor to emit `BATTERY_LOW` at `<=20` and `BATTERY_CRITICAL` at `<=10`.

- [ ] **Step 4: Run event service tests**

Run: `python -m pytest tests/test_vehicle_event_service.py tests/test_vehicle_state_monitor_agent.py -q`

Expected: PASS.

### Task 2: Web API Integration

**Files:**
- Modify: `web_demo/app_model.py`
- Modify: `web_demo/server.py`
- Test: `tests/test_web_demo_app_model.py`
- Test: `tests/test_web_server_config.py`

- [ ] **Step 1: Write failing tests**

```python
from web_demo.app_model import get_vehicle_events_payload, reset_vehicle_state, update_vehicle_state
from web_demo.server import WebDemoHandler


def test_vehicle_events_payload_is_independent_from_command_execution():
    reset_vehicle_state()
    update_vehicle_state({"battery_percent": 18})
    payload = get_vehicle_events_payload()

    assert payload["events"][0]["type"] == "BATTERY_LOW"
    assert payload["events"][0]["trigger"] == "AUTO"


def test_vehicle_events_path_is_registered():
    assert "/api/vehicle-events" in WebDemoHandler.GET_ROUTES
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest tests/test_web_demo_app_model.py tests/test_web_server_config.py -q`

Expected: FAIL because function and route are missing.

- [ ] **Step 3: Implement API**

Use `VehicleEventService` in `get_initial_payload`, `update_vehicle_state`, and `get_vehicle_events_payload`. Add `GET /api/vehicle-events` in the web server.

- [ ] **Step 4: Run web tests**

Run: `python -m pytest tests/test_web_demo_app_model.py tests/test_web_server_config.py -q`

Expected: PASS.

### Task 3: Frontend Polling

**Files:**
- Modify: `web_demo/static/app.js`
- Modify: `web_demo/static/styles.css`
- Test: `tests/test_web_demo_frontend_logic.py`

- [ ] **Step 1: Write failing frontend logic test**

```python
def test_frontend_polls_vehicle_events():
    script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

    assert "/api/vehicle-events" in script
    assert "startVehicleEventPolling" in script
    assert "setInterval" in script
    assert "event.severity" in script
```

- [ ] **Step 2: Run frontend test and verify failure**

Run: `python -m pytest tests/test_web_demo_frontend_logic.py -q`

Expected: FAIL because polling is missing.

- [ ] **Step 3: Implement polling and severity rendering**

Fetch `/api/vehicle-events` every 3 seconds, call `renderVehicle` and `renderAutoEvents`, and add severity classes for warning and critical events.

- [ ] **Step 4: Run frontend tests**

Run: `python -m pytest tests/test_web_demo_frontend_logic.py -q`

Expected: PASS.

### Task 4: Verification And Restart

**Files:**
- No code changes.

- [ ] **Step 1: Run full tests**

Run: `python -m pytest tests`

Expected: all tests pass.

- [ ] **Step 2: Restart local web demo**

Restart `web_demo.server` on port `8031`.

- [ ] **Step 3: Smoke test API**

POST `/api/vehicle-state` with `battery_percent=8`, then GET `/api/vehicle-events`.

Expected: event type `BATTERY_CRITICAL`, severity `CRITICAL`.
