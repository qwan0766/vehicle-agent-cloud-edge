# Destination Clarification Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert fuzzy or low-confidence navigation destinations from hard provider failures into a normal `NEEDS_CLARIFICATION` business state, then let the user refine the destination and resume routing without losing the original intent.

**Architecture:** The vehicle core remains the single orchestration boundary. `LocalIntentAgent` classifies the command, `GlobalSafetyDispatchAgent` enforces safety, `DestinationResolver` performs local confidence checks before cloud dispatch, a small persistent pending-clarification store keeps unresolved destination questions across web requests, and the web demo renders clarification prompts as first-class results. Online mode still uses real providers when the destination is concrete; it does not silently fall back to offline data.

**Tech Stack:** Python 3.8-3.11, standard-library JSON persistence, existing LangGraph orchestration, existing provider adapters, vanilla JavaScript frontend, `pytest`.

---

## File Structure

- Modify: `core/constants.py`  
  Add `ExecutionStatus.NEEDS_CLARIFICATION`.
- Modify: `core/vehicle_core_service.py`  
  Return clarification results before cloud dispatch and support follow-up destination refinements.
- Create: `core/clarification.py`  
  Centralize clarification payload building, refinement detection, and destination command reconstruction.
- Create: `memory/pending_clarification_store.py`  
  Persist pending clarification state by user and session so the web demo can handle follow-up input across HTTP requests.
- Modify: `providers/destination_resolver.py`  
  Keep deterministic local ambiguity checks, but expose enough structured data for business-level clarification handling.
- Modify: `web_demo/app_model.py`  
  Include `clarification` in API payloads, suppress route/provider panels for clarification results, and add a clear agent trace.
- Modify: `web_demo/server.py`  
  Stop returning HTTP 502 for destination clarification. Keep real provider failures as errors.
- Modify: `web_demo/static/app.js`  
  Render clarification cards, suggestions, and click-to-fill suggestion chips.
- Modify: `web_demo/static/styles.css`  
  Add compact styles for clarification prompts and suggestion buttons.
- Add or modify: `tests/test_clarification_loop.py`  
  Cover service-level clarification, follow-up reconstruction, and no-cloud-dispatch behavior.
- Modify: `tests/test_destination_resolver.py`  
  Verify broad region, unclear short destination, and unknown chain qualifier behavior.
- Modify: `tests/test_web_demo_app_model.py`  
  Verify `/api/run` payload shape for `NEEDS_CLARIFICATION`.
- Modify: `tests/test_web_error_response.py`  
  Verify destination clarification is no longer treated as provider failure.
- Modify: `tests/test_web_demo_frontend_logic.py`  
  Verify frontend support for clarification payloads and suggestion chips.
- Modify: `tests/test_input_matrix.py`  
  Add broad and ambiguous destination cases to the regression matrix.
- Modify: `docs/superpowers/specs/2026-05-07-destination-clarification-loop-design.md`  
  Update with implementation notes if the final contract differs in naming only.

---

## Task 1: Add Clarification Status To The Core Contract

**Files:**

- Modify: `core/constants.py`
- Modify: `core/vehicle_core_service.py`
- Test: `tests/test_clarification_loop.py`

- [ ] **Step 1: Write the failing status contract test**

Create `tests/test_clarification_loop.py` with a first test that imports `ExecutionStatus.NEEDS_CLARIFICATION` and asserts its value:

```python
from core.constants import ExecutionStatus


def test_execution_status_has_needs_clarification():
    assert ExecutionStatus.NEEDS_CLARIFICATION.value == "NEEDS_CLARIFICATION"
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_clarification_loop.py -p no:cacheprovider
```

Expected result: failure because `ExecutionStatus.NEEDS_CLARIFICATION` does not exist.

- [ ] **Step 3: Implement the status**

Add this enum member in `core/constants.py`:

```python
NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
```

- [ ] **Step 4: Extend `ExecutionResult`**

Add a `clarification: dict = None` field to `ExecutionResult` in `core/vehicle_core_service.py`. Preserve all existing fields and ensure `_complete_result()` and `_with_feedback()` pass `clarification` through when reconstructing `ExecutionResult`.

- [ ] **Step 5: Re-run the focused test**

Expected result: the status contract test passes.

---

## Task 2: Build A Structured Clarification Payload Helper

**Files:**

- Create: `core/clarification.py`
- Modify: `providers/destination_resolver.py` only if the exception lacks a field needed by the helper
- Test: `tests/test_clarification_loop.py`

- [ ] **Step 1: Write payload tests first**

Add tests for:

- `build_destination_clarification()` returns `type`, `query`, `reason`, `question`, `suggestions`, and `candidates`.
- Broad region example: `query="北京"` produces a question that asks for a concrete destination.
- Unknown chain qualifier example: `query="霓虹蔚来中心"` produces wording that explains multiple or uncertain chain-store candidates.
- The helper keeps provider candidates optional and defaults to an empty list.

Expected test shape:

```python
from core.clarification import build_destination_clarification
from providers.destination_resolver import DestinationClarificationRequired


def test_build_destination_clarification_payload():
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
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_clarification_loop.py -p no:cacheprovider
```

- [ ] **Step 3: Implement `core/clarification.py`**

Implement these public functions:

- `build_destination_clarification(exc, original_content: str) -> dict`
- `is_destination_refinement(content: str, pending: dict) -> bool`
- `reconstruct_destination_command(content: str, pending: dict) -> str`

Behavior:

- `build_destination_clarification()` never raises for missing suggestions.
- `question` is deterministic and reason-based.
- `is_destination_refinement()` returns `True` when there is a pending destination clarification and the new input looks like a destination fragment rather than a new car-control, safety, personalize, or charge-plan command.
- `reconstruct_destination_command()` combines the original navigation prefix with the refined destination. Example: pending `导航去北京`, follow-up `东方广场蔚来中心` becomes `导航去北京东方广场蔚来中心`.

- [ ] **Step 4: Re-run the focused tests**

Expected result: all clarification helper tests pass.

---

## Task 3: Persist Pending Clarification Across Requests

**Files:**

- Create: `memory/pending_clarification_store.py`
- Modify: `core/vehicle_core_service.py`
- Test: `tests/test_clarification_loop.py`

- [ ] **Step 1: Write persistence tests first**

Add tests that use `tmp_path`:

- `save()` writes pending state keyed by `user_id` and `session_id`.
- `get()` returns the saved payload.
- `clear()` removes only the matching pending clarification.
- A second user does not receive the first user's pending state.

Expected test shape:

```python
from memory.pending_clarification_store import PendingClarificationStore


def test_pending_clarification_store_is_user_scoped(tmp_path):
    store = PendingClarificationStore(tmp_path / "pending.json")
    store.save("user_001", "default", {"query": "北京"})

    assert store.get("user_001", "default")["query"] == "北京"
    assert store.get("user_002", "default") is None
```

- [ ] **Step 2: Implement the store**

Use standard-library JSON only. The file shape should be easy to inspect:

```json
{
  "user_001:default": {
    "type": "destination",
    "query": "北京"
  }
}
```

Implementation constraints:

- Create the parent directory automatically.
- Return `None` for missing or invalid files.
- Keep writes atomic enough for this local demo by writing a full JSON snapshot.

- [ ] **Step 3: Add service constructor injection**

Modify `VehicleCoreService.__init__()`:

```python
pending_clarification_store=None
```

Default to `PendingClarificationStore()` so `web_demo.app_model.run_command()` works even though it creates a fresh service per HTTP request.

- [ ] **Step 4: Re-run persistence tests**

Expected result: all persistence tests pass.

---

## Task 4: Convert Ambiguous Destination To A Normal Service Result

**Files:**

- Modify: `core/vehicle_core_service.py`
- Modify: `core/clarification.py`
- Test: `tests/test_clarification_loop.py`

- [ ] **Step 1: Write service tests first**

Add a fake cloud agent that fails if invoked:

```python
class FailingCloudAgent:
    def dispatch(self, msg):
        raise AssertionError("cloud should not run before clarification")

    def get_last_trace(self):
        return []

    def get_last_graph(self):
        return {}
```

Test cases:

- `导航去北京` returns `ExecutionStatus.NEEDS_CLARIFICATION`.
- `导航去高老庄` returns `ExecutionStatus.NEEDS_CLARIFICATION`.
- `导航去霓虹蔚来中心` returns `ExecutionStatus.NEEDS_CLARIFICATION`.
- Each result has `message.command_type == CommandType.NAVIGATION`.
- Each result has `safety == SAFE`.
- Each result has `clarification["type"] == "destination"`.
- Cloud dispatch is not called.
- Feedback recording does not mark the result as executed.

- [ ] **Step 2: Run the service tests and confirm failure**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_clarification_loop.py -p no:cacheprovider
```

- [ ] **Step 3: Implement the pre-cloud clarification gate**

Inside `VehicleCoreService.run()`:

1. After intent recognition and safety evaluation pass.
2. Before offline fallback or online cloud dispatch.
3. For `CommandType.NAVIGATION` and `CommandType.CHARGE_PLAN` only when a concrete destination is required.
4. Call `resolve_destination_detail(user_input, geocoder=None)` as a local ambiguity gate.
5. Catch `DestinationClarificationRequired`.
6. Build clarification payload.
7. Persist pending clarification.
8. Return:

```python
ExecutionResult(
    status=ExecutionStatus.NEEDS_CLARIFICATION,
    output=clarification["question"],
    message=msg,
    clarification=clarification,
)
```

Do not catch real provider errors here. Online provider failures must still surface as failures because the user explicitly requested no offline fallback for online demo failures.

- [ ] **Step 4: Re-run service tests**

Expected result: clarification cases pass and existing execution/block/fallback tests still pass.

---

## Task 5: Support Follow-Up Destination Refinement

**Files:**

- Modify: `core/vehicle_core_service.py`
- Modify: `core/clarification.py`
- Test: `tests/test_clarification_loop.py`

- [ ] **Step 1: Write follow-up tests first**

Test cases:

- First request `导航去北京` returns `NEEDS_CLARIFICATION` and saves pending state.
- Next request `东方广场蔚来中心` is reconstructed to `导航去北京东方广场蔚来中心`.
- Next request with a complete command `导航去上海外滩` is treated as a new command, not as a refinement.
- Next request `温度调到24度` clears or ignores pending navigation clarification and executes car control normally.
- Dangerous follow-up `关闭AEB` is blocked and does not route through clarification reconstruction.

Use a fake cloud agent that records `msg.content`:

```python
class RecordingCloudAgent:
    def __init__(self):
        self.contents = []

    def dispatch(self, msg):
        self.contents.append(msg.content)
        return "route ok"
```

- [ ] **Step 2: Implement follow-up handling**

At the start of `VehicleCoreService.run()`:

1. Load pending clarification by `user_id` and session `"default"`.
2. If pending exists and `is_destination_refinement(user_input, pending)` is true, reconstruct `user_input`.
3. Continue normal intent and safety processing with the reconstructed input.
4. Clear pending state after an executed, blocked, or provider-failed attempt that is no longer asking for the same clarification.

Safety rule:

- Run safety evaluation after reconstruction.
- If the follow-up text itself contains dangerous vehicle-control content, do not reconstruct it as a destination.

- [ ] **Step 3: Re-run follow-up tests**

Expected result: the service can complete a two-turn clarification loop without needing a long-lived web server process.

---

## Task 6: Return HTTP 200 And Structured Payloads In The Web Model

**Files:**

- Modify: `web_demo/app_model.py`
- Modify: `web_demo/server.py`
- Test: `tests/test_web_demo_app_model.py`
- Test: `tests/test_web_error_response.py`

- [ ] **Step 1: Write app model tests first**

Add tests for `run_command("导航去北京", user_id="user_001", network="ONLINE")`:

- `payload["result"]["status"] == "NEEDS_CLARIFICATION"`.
- `payload["result"]["clarification"]["type"] == "destination"`.
- `payload["result"]["clarification"]["query"] == "北京"`.
- `payload["route_summary"]` is empty or marked unavailable because route planning has not run.
- `payload["charge_stations"]` is empty.
- `payload["agent_trace"]` includes `"DestinationClarification"` and does not include `"GlobalTripPlanningAgent"`.
- `payload["runtime_trace"]` is empty or contains only local clarification trace entries.

- [ ] **Step 2: Write server behavior tests**

Update `tests/test_web_error_response.py` or add a server-level test so destination clarification is not asserted as a 502 provider error. Keep tests for `AMap route error`, `AMap geocode error`, timeout, and DeepSeek failure as error responses.

- [ ] **Step 3: Implement `app_model` payload support**

In `run_command()` include:

```python
"result": {
    "status": result.status.value,
    "output": result.output,
    "clarification": result.clarification or {},
}
```

Guard route and charge helper calls:

- If `result.status == ExecutionStatus.NEEDS_CLARIFICATION`, return empty route summary and empty charge stations.
- If `result.status == ExecutionStatus.BLOCKED`, keep existing safe behavior.
- If `result.status == ExecutionStatus.EXECUTED`, keep existing route and charge behavior.

Update `_agent_trace()`:

- For `NEEDS_CLARIFICATION`, return:

```python
["LocalIntentAgent", "GlobalSafetyDispatchAgent", "DestinationClarification", "DataUploadAgent"]
```

- [ ] **Step 4: Implement server behavior**

`web_demo/server.py` should not need to catch `DestinationClarificationRequired` after the service conversion. Remove the special destination-clarification block from `build_error_response()` only after tests prove no production path uses it. If retained for defensive coverage, it should not be used by `/api/run` for ordinary clarification.

- [ ] **Step 5: Re-run web tests**

Expected result: app model and web error response tests pass.

---

## Task 7: Render Clarification In The Frontend

**Files:**

- Modify: `web_demo/static/app.js`
- Modify: `web_demo/static/styles.css`
- Test: `tests/test_web_demo_frontend_logic.py`
- Test: `tests/test_web_demo_markup.py`

- [ ] **Step 1: Write frontend tests first**

Add or update tests that inspect `web_demo/static/app.js` for:

- A `renderClarification` function.
- `NEEDS_CLARIFICATION` status handling.
- Suggestion chips/buttons that fill `#commandInput`.
- Clarification output rendered separately from `commandError`.

Add or update markup/style tests for:

- A CSS class such as `.clarification-card`.
- A CSS class such as `.clarification-suggestions`.

- [ ] **Step 2: Implement rendering logic**

In `renderCommandResult(payload)` or the equivalent frontend result renderer:

1. If `payload.result.status === "NEEDS_CLARIFICATION"`, call `renderClarification(payload.result.clarification)`.
2. Set the top-right status badge to wording such as `需要确认`.
3. Do not set `commandError`.
4. Render `question`, `reason`, and suggestions in the result area.
5. Each suggestion button writes the suggestion text to `nodes.commandInput.value` and focuses the input.

- [ ] **Step 3: Style the card**

Use restrained dashboard styling:

- 8px or smaller radius.
- No nested cards.
- Compact button chips.
- Clear status color distinct from danger red.

- [ ] **Step 4: Re-run frontend tests**

Expected result: frontend logic and markup tests pass.

---

## Task 8: Expand The Regression Matrix

**Files:**

- Modify: `tests/test_destination_resolver.py`
- Modify: `tests/test_input_matrix.py`
- Modify: `tests/test_vehicle_core_service.py`
- Test: full test suite

- [ ] **Step 1: Add destination ambiguity cases**

Add cases for:

- `导航去北京` -> `NEEDS_CLARIFICATION`.
- `导航去上海` -> `NEEDS_CLARIFICATION`.
- `导航去高老庄` -> `NEEDS_CLARIFICATION`.
- `导航去霓虹蔚来中心` -> `NEEDS_CLARIFICATION`.
- `导航去北京东方广场蔚来中心` -> proceeds to online routing if providers are available in that test path.
- `导航去上海外滩` -> concrete enough for routing.
- `导航去121.48,31.23` -> concrete GPS and no clarification.
- `打开座椅加热` -> car control and no destination clarification.
- `电量低` -> charge plan and no arbitrary city destination clarification.
- `关闭AEB` -> `BLOCKED`.

- [ ] **Step 2: Add follow-up cases**

Add two-turn matrix cases:

- `导航去北京` then `东方广场蔚来中心`.
- `导航去高老庄` then `北京市朝阳区望京`.
- `导航去上海` then `温度调到24度`.
- `导航去霓虹蔚来中心` then `关闭AEB`.

- [ ] **Step 3: Run focused matrix tests**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests/test_destination_resolver.py tests/test_input_matrix.py tests/test_vehicle_core_service.py tests/test_clarification_loop.py -p no:cacheprovider
```

Expected result: all focused matrix tests pass.

---

## Task 9: Verify The Browser Demo Contract

**Files:**

- Modify only files needed by failed checks from previous tasks.
- Test: `web_demo/server.py` through HTTP.

- [ ] **Step 1: Start or restart the demo server**

Use an available port:

```powershell
Start-Process -FilePath "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -ArgumentList @("-m","web_demo.server","--host","127.0.0.1","--port","8031") -WorkingDirectory "E:\claudeCode\weilaiAgent" -WindowStyle Hidden
```

- [ ] **Step 2: Probe clarification through HTTP**

Run:

```powershell
$body = @{ content = "导航去北京"; user_id = "user_001"; network = "ONLINE" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/api/run" -ContentType "application/json" -Body $body
```

Expected result:

- HTTP succeeds.
- JSON has `result.status = NEEDS_CLARIFICATION`.
- JSON has `result.clarification.question`.
- JSON does not have top-level `error`.

- [ ] **Step 3: Probe follow-up through HTTP**

Run:

```powershell
$body = @{ content = "东方广场蔚来中心"; user_id = "user_001"; network = "ONLINE" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/api/run" -ContentType "application/json" -Body $body
```

Expected result:

- The request is treated as a refinement for the pending Beijing destination.
- It either proceeds into online route planning or returns a provider error based on real API behavior.
- It must not route to a fabricated destination.

- [ ] **Step 4: Open the browser demo**

Open:

```text
http://127.0.0.1:8031/
```

Manual checks:

- `导航去北京` shows a normal clarification card, not a red provider error.
- Suggestion chips fill the input.
- `关闭AEB` remains blocked.
- `打开座椅加热` does not show destination clarification.
- `导航去霓虹蔚来中心` asks for a more concrete destination before routing.

---

## Task 10: Full Verification And Commit

**Files:**

- All modified files.

- [ ] **Step 1: Run the full test suite**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) ("pytest-tmp-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests --basetemp=$basetemp -p no:cacheprovider
```

Expected result: all tests pass. The existing LangGraph `allowed_objects` warning is acceptable if no new warnings appear.

- [ ] **Step 2: Run a git diff review**

Run:

```powershell
git diff -- core providers memory web_demo tests docs
git status --short
```

Review for:

- No API keys or `.env` content.
- No unrelated formatting churn.
- No fake route data in online demo paths.
- No broad exception swallowing around provider calls.

- [ ] **Step 3: Commit the implementation**

Run:

```powershell
git add core providers memory web_demo tests docs
git commit -m "feat: add destination clarification loop"
```

Expected result: one commit containing the implementation and tests.

---

## Acceptance Criteria

- `导航去北京` returns `NEEDS_CLARIFICATION`, not `EXECUTED` and not HTTP 502.
- `导航去霓虹蔚来中心` asks for clarification and does not invent a matching NIO center.
- `导航去北京` followed by `东方广场蔚来中心` reconstructs a concrete navigation command.
- Car-control, personalization, and dangerous commands are not affected by destination clarification.
- Online mode continues to fail visibly for real provider failures and does not use offline route fallback.
- Frontend renders markdown output for executed results and a dedicated clarification card for clarification results.
- Full test suite passes.
