# Web Frontend Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `web_demo/static/app.js` into native ES modules while preserving the current UI, API contract, and demo behavior.

**Architecture:** Keep a dependency-free browser frontend. `app.js` becomes a thin entrypoint, shared state lives in `js/state.js`, DOM lookup lives in `js/dom.js`, API calls live in `js/api.js`, user interactions live in `js/events.js`, and each visible panel gets a focused renderer module.

**Tech Stack:** Python test suite, static HTML/CSS/JavaScript, native browser ES Modules, existing Python Web server.

---

## File Structure

Create:

- `web_demo/static/js/api.js`
- `web_demo/static/js/state.js`
- `web_demo/static/js/dom.js`
- `web_demo/static/js/events.js`
- `web_demo/static/js/markdown.js`
- `web_demo/static/js/renderers/vehicle.js`
- `web_demo/static/js/renderers/demo.js`
- `web_demo/static/js/renderers/result.js`
- `web_demo/static/js/renderers/trace.js`
- `web_demo/static/js/renderers/rag.js`
- `web_demo/static/js/renderers/feedback.js`
- `web_demo/static/js/renderers/providers.js`
- `web_demo/static/js/renderers/acceptance.js`
- `web_demo/static/js/renderers/route.js`
- `web_demo/static/js/renderers/local-context.js`

Modify:

- `web_demo/static/app.js`
- `web_demo/static/index.html`
- `tests/test_web_demo_frontend_logic.py`

Do not modify backend API behavior in this plan.

---

### Task 1: Add Frontend Module Structure Tests

**Files:**
- Modify: `tests/test_web_demo_frontend_logic.py`

- [ ] **Step 1: Add failing tests for module layout**

Append these tests to `TestWebDemoFrontendLogic`:

```python
    def test_frontend_uses_native_es_modules(self):
        markup = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        app = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn('type="module"', markup)
        self.assertIn('src="/app.js"', markup)
        self.assertIn("import { getInitialState } from './js/api.js';", app)
        self.assertIn("import { bindEvents } from './js/events.js';", app)

    def test_frontend_modules_exist_with_expected_responsibilities(self):
        expected_files = [
            "web_demo/static/js/api.js",
            "web_demo/static/js/state.js",
            "web_demo/static/js/dom.js",
            "web_demo/static/js/events.js",
            "web_demo/static/js/markdown.js",
            "web_demo/static/js/renderers/vehicle.js",
            "web_demo/static/js/renderers/demo.js",
            "web_demo/static/js/renderers/result.js",
            "web_demo/static/js/renderers/trace.js",
            "web_demo/static/js/renderers/rag.js",
            "web_demo/static/js/renderers/feedback.js",
            "web_demo/static/js/renderers/providers.js",
            "web_demo/static/js/renderers/acceptance.js",
            "web_demo/static/js/renderers/route.js",
            "web_demo/static/js/renderers/local-context.js",
        ]
        for path in expected_files:
            self.assertTrue(Path(path).exists(), path)

        api = Path("web_demo/static/js/api.js").read_text(encoding="utf-8")
        self.assertIn('fetch("/api/state")', api)
        self.assertIn('fetch("/api/run"', api)
        self.assertIn('fetch("/api/vehicle-state"', api)
        self.assertIn('fetch("/api/vehicle-events")', api)

        events = Path("web_demo/static/js/events.js").read_text(encoding="utf-8")
        self.assertIn("requestId !== state.activeRequestId", events)
        self.assertIn("renderVehicle(payload.vehicle_state, { syncControls: false, syncNetwork: false })", events)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests\test_web_demo_frontend_logic.py -q
```

Expected: FAIL because module files do not exist and `index.html` does not load `type="module"` yet.

---

### Task 2: Extract Shared State, DOM Lookup, API, and Markdown

**Files:**
- Create: `web_demo/static/js/state.js`
- Create: `web_demo/static/js/dom.js`
- Create: `web_demo/static/js/api.js`
- Create: `web_demo/static/js/markdown.js`
- Modify: `web_demo/static/app.js`

- [ ] **Step 1: Create `state.js`**

Move the current top-level `state` object from `app.js` into:

```javascript
export const state = {
  network: "ONLINE",
  scenarios: [],
  demoSteps: [],
  users: [],
  userId: "user_001",
  activeDemoId: "",
  requestSeq: 0,
  activeRequestId: 0,
};
```

- [ ] **Step 2: Create `dom.js`**

Move the current top-level `nodes` object from `app.js` into `dom.js` and export it:

```javascript
export const nodes = {
  networkBadge: document.querySelector("#networkBadge"),
  safetyBadge: document.querySelector("#safetyBadge"),
  gpsValue: document.querySelector("#gpsValue"),
  speedValue: document.querySelector("#speedValue"),
  batteryValue: document.querySelector("#batteryValue"),
  batteryBar: document.querySelector("#batteryBar"),
  roadTypeValue: document.querySelector("#roadTypeValue"),
  speedLimitValue: document.querySelector("#speedLimitValue"),
  assistModeValue: document.querySelector("#assistModeValue"),
  roadTypeInput: document.querySelector("#roadTypeInput"),
  speedLimitInput: document.querySelector("#speedLimitInput"),
  vehicleSpeedInput: document.querySelector("#vehicleSpeedInput"),
  batteryInput: document.querySelector("#batteryInput"),
  assistModeInput: document.querySelector("#assistModeInput"),
  updateVehicleStateBtn: document.querySelector("#updateVehicleStateBtn"),
  autoEvents: document.querySelector("#autoEvents"),
  onlineBtn: document.querySelector("#onlineBtn"),
  offlineBtn: document.querySelector("#offlineBtn"),
  userIdValue: document.querySelector("#userIdValue"),
  userSelect: document.querySelector("#userSelect"),
  scenarioButtons: document.querySelector("#scenarioButtons"),
  commandInput: document.querySelector("#commandInput"),
  runBtn: document.querySelector("#runBtn"),
  commandError: document.querySelector("#commandError"),
  demoStepCount: document.querySelector("#demoStepCount"),
  demoSteps: document.querySelector("#demoSteps"),
  demoFocus: document.querySelector("#demoFocus"),
  demoTalkTrack: document.querySelector("#demoTalkTrack"),
  demoExpectedPanels: document.querySelector("#demoExpectedPanels"),
  traceMode: document.querySelector("#traceMode"),
  graphMode: document.querySelector("#graphMode"),
  graphPath: document.querySelector("#graphPath"),
  agentTrace: document.querySelector("#agentTrace"),
  runtimeTrace: document.querySelector("#runtimeTrace"),
  ragCount: document.querySelector("#ragCount"),
  ragContext: document.querySelector("#ragContext"),
  feedbackStatus: document.querySelector("#feedbackStatus"),
  feedbackEvent: document.querySelector("#feedbackEvent"),
  feedbackPreference: document.querySelector("#feedbackPreference"),
  localContextWindow: document.querySelector("#localContextWindow"),
  localContextProvider: document.querySelector("#localContextProvider"),
  localContextModel: document.querySelector("#localContextModel"),
  localContextSummary: document.querySelector("#localContextSummary"),
  localContextRecent: document.querySelector("#localContextRecent"),
  localContextPrompt: document.querySelector("#localContextPrompt"),
  evalTotal: document.querySelector("#evalTotal"),
  evalIntent: document.querySelector("#evalIntent"),
  evalSafety: document.querySelector("#evalSafety"),
  evalRag: document.querySelector("#evalRag"),
  acceptanceRefreshBtn: document.querySelector("#acceptanceRefreshBtn"),
  acceptanceStatus: document.querySelector("#acceptanceStatus"),
  acceptanceTime: document.querySelector("#acceptanceTime"),
  acceptanceSteps: document.querySelector("#acceptanceSteps"),
  smokeBtn: document.querySelector("#smokeBtn"),
  providerLlm: document.querySelector("#providerLlm"),
  providerLocalLlm: document.querySelector("#providerLocalLlm"),
  providerOrchestrator: document.querySelector("#providerOrchestrator"),
  providerMap: document.querySelector("#providerMap"),
  providerWeather: document.querySelector("#providerWeather"),
  providerCharge: document.querySelector("#providerCharge"),
  smokeResults: document.querySelector("#smokeResults"),
  routeProvider: document.querySelector("#routeProvider"),
  routeDistance: document.querySelector("#routeDistance"),
  routeDuration: document.querySelector("#routeDuration"),
  routeStrategy: document.querySelector("#routeStrategy"),
  chargeStations: document.querySelector("#chargeStations"),
  requestIdValue: document.querySelector("#requestIdValue"),
  commandTypeValue: document.querySelector("#commandTypeValue"),
  safetyValue: document.querySelector("#safetyValue"),
  executionValue: document.querySelector("#executionValue"),
  resultOutput: document.querySelector("#resultOutput"),
};
```

- [ ] **Step 3: Create `api.js`**

Move `parseJsonResponse` and fetch calls into:

```javascript
export async function getInitialState() {
  const response = await fetch("/api/state");
  return parseJsonResponse(response);
}

export async function runCommandRequest(payload) {
  const response = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function updateVehicleStateRequest(payload) {
  const response = await fetch("/api/vehicle-state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonResponse(response);
}

export async function getVehicleEvents() {
  const response = await fetch("/api/vehicle-events");
  return parseJsonResponse(response);
}

export async function runProviderSmokeTestRequest() {
  const response = await fetch("/api/provider-smoke", { method: "POST" });
  return parseJsonResponse(response);
}

export async function getAcceptance() {
  const response = await fetch("/api/acceptance");
  return parseJsonResponse(response);
}

export async function parseJsonResponse(response) {
  const payload = await response.json();
  if (!response.ok) {
    const errorInfo = payload.error || {};
    const message = errorInfo.user_message || errorInfo.message || `HTTP ${response.status}`;
    const error = new Error(message);
    error.info = errorInfo;
    throw error;
  }
  return payload;
}
```

- [ ] **Step 4: Create `markdown.js`**

Move `renderMarkdown`, `markdownToHtml`, `formatInline`, and `escapeHtml` into `markdown.js`. Export:

```javascript
export function renderMarkdown(target, markdown) {
  target.innerHTML = markdownToHtml(markdown || "");
}

export function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
```

Keep the existing `markdownToHtml` and `formatInline` implementation exactly as-is.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests\test_web_demo_frontend_logic.py -q
```

Expected: still FAIL because renderers and `type="module"` are not complete yet, but no syntax errors should be introduced in Python tests.

---

### Task 3: Extract Vehicle, Demo, Acceptance, Provider, Route, RAG, Feedback, and Local Context Renderers

**Files:**
- Create: `web_demo/static/js/renderers/vehicle.js`
- Create: `web_demo/static/js/renderers/demo.js`
- Create: `web_demo/static/js/renderers/acceptance.js`
- Create: `web_demo/static/js/renderers/providers.js`
- Create: `web_demo/static/js/renderers/route.js`
- Create: `web_demo/static/js/renderers/rag.js`
- Create: `web_demo/static/js/renderers/feedback.js`
- Create: `web_demo/static/js/renderers/local-context.js`
- Modify: `web_demo/static/app.js`

- [ ] **Step 1: Create `vehicle.js`**

Move and export:

```javascript
export function renderVehicle(vehicle, options = {}) { /* existing implementation */ }
export function renderAutoEvents(events, rules) { /* existing implementation */ }
export function formatPercent(value) { return `${Math.round(Number(value) * 100)}%`; }
```

Import `escapeHtml` from `../markdown.js`.

- [ ] **Step 2: Create `demo.js`**

Move and export:

```javascript
export function renderUsers(nodes, state) { /* existing implementation */ }
export function renderScenarioButtons(nodes, state, setNetwork, runCommand) { /* existing implementation */ }
export function renderDemoSteps(nodes, state, setNetwork, runCommand) { /* existing implementation */ }
export function activateDemoStep(nodes, state, step, shouldRun, setNetwork, runCommand) { /* existing implementation */ }
export function renderDemoNotes(nodes, step) { /* existing implementation */ }
export function renderOfflineEvaluation(nodes, report) { /* existing implementation */ }
```

The functions receive `nodes` and `state` explicitly to avoid hidden renderer dependencies.

- [ ] **Step 3: Create `acceptance.js`**

Move and export:

```javascript
export function renderAcceptance(nodes, report) { /* existing implementation */ }
```

- [ ] **Step 4: Create `providers.js`**

Move and export:

```javascript
export function renderProviders(nodes, providers) { /* existing implementation */ }
export function renderSmokeResults(nodes, results) { /* existing implementation */ }
```

- [ ] **Step 5: Create `route.js`**

Move and export:

```javascript
export function renderRouteSummary(nodes, route, stations) { /* existing implementation */ }
```

- [ ] **Step 6: Create `rag.js`**

Move and export:

```javascript
export function renderRagContext(nodes, items) { /* existing implementation */ }
```

Import `escapeHtml` from `../markdown.js`.

- [ ] **Step 7: Create `feedback.js`**

Move and export:

```javascript
export function renderFeedback(nodes, feedback) { /* existing implementation */ }
```

- [ ] **Step 8: Create `local-context.js`**

Move and export:

```javascript
export function renderLocalContext(nodes, context) { /* existing implementation */ }
```

- [ ] **Step 9: Run focused tests**

Run:

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests\test_web_demo_frontend_logic.py -q
```

Expected: still may fail until result/trace/events extraction is complete.

---

### Task 4: Extract Result and Trace Renderers

**Files:**
- Create: `web_demo/static/js/renderers/result.js`
- Create: `web_demo/static/js/renderers/trace.js`
- Modify: `web_demo/static/app.js`

- [ ] **Step 1: Create `trace.js`**

Move and export:

```javascript
export function renderRuntimeTrace(nodes, items, status = "") { /* existing implementation */ }
export function renderGraphPath(nodes, graph) { /* existing implementation */ }
export function agentClass(agent) { /* existing implementation */ }
```

- [ ] **Step 2: Create `result.js`**

Move and export:

```javascript
export function renderResult(nodes, payload, runCommand) { /* existing implementation */ }
export function renderClarification(nodes, clarification, fallbackOutput, runCommand) { /* existing implementation */ }
export function renderCommandError(nodes, error, renderHelpers) { /* existing implementation */ }
export function clearCommandError(nodes) { /* existing implementation */ }
export function errorInfoToHtml(title, message, info) { /* existing implementation */ }
```

`renderHelpers` should include:

```javascript
{
  renderGraphPath,
  renderLocalContext,
  renderRouteSummary,
}
```

This keeps `result.js` from importing every panel renderer directly.

- [ ] **Step 3: Preserve status-specific rendering**

Ensure `renderResult` still contains checks for:

```javascript
const needsClarification = result.status === "NEEDS_CLARIFICATION";
const needsDriverConfirmation = result.status === "NEEDS_DRIVER_CONFIRMATION";
const needsChargeConfirmation = result.status === "NEEDS_CHARGE_CONFIRMATION";
```

Ensure `renderCommandError` still adds:

```javascript
["LocalIntentAgent", "GlobalSafetyDispatchAgent", "ProviderError"]
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests\test_web_demo_frontend_logic.py -q
```

Expected: failures should now be limited to `app.js` entrypoint, `events.js`, or `index.html`.

---

### Task 5: Extract Event Orchestration and Thin Entrypoint

**Files:**
- Create: `web_demo/static/js/events.js`
- Modify: `web_demo/static/app.js`
- Modify: `web_demo/static/index.html`

- [ ] **Step 1: Create `events.js`**

Move and export:

```javascript
export function bindEvents(deps) { /* existing bindEvents implementation adapted to deps */ }
export function setNetwork(nodes, state, network) { /* existing implementation */ }
export async function updateVehicleState(deps) { /* existing implementation */ }
export function startVehicleEventPolling(deps) { /* existing implementation */ }
export async function refreshVehicleEvents(deps) { /* existing implementation */ }
export async function refreshAcceptance(deps) { /* existing implementation */ }
export async function runSmokeTest(deps) { /* existing implementation */ }
export async function runCommand(deps) { /* existing implementation */ }
```

`deps` must contain:

```javascript
{
  nodes,
  state,
  api,
  renderers,
}
```

Keep this exact stale-response guard inside `runCommand`:

```javascript
if (requestId !== state.activeRequestId) {
  return;
}
```

Keep this exact polling update inside `refreshVehicleEvents`:

```javascript
renderVehicle(payload.vehicle_state, { syncControls: false, syncNetwork: false });
```

- [ ] **Step 2: Convert `app.js` into a thin entrypoint**

Replace `web_demo/static/app.js` with an entrypoint that imports modules and initializes:

```javascript
import { getInitialState, getAcceptance, getVehicleEvents, runCommandRequest, runProviderSmokeTestRequest, updateVehicleStateRequest } from "./js/api.js";
import { nodes } from "./js/dom.js";
import { state } from "./js/state.js";
import { bindEvents, setNetwork } from "./js/events.js";
import { renderAcceptance } from "./js/renderers/acceptance.js";
import { renderDemoSteps, renderOfflineEvaluation, renderScenarioButtons, renderUsers } from "./js/renderers/demo.js";
import { renderAutoEvents, renderVehicle } from "./js/renderers/vehicle.js";
import { renderProviders } from "./js/renderers/providers.js";
import { renderCommandError } from "./js/renderers/result.js";

const api = {
  getAcceptance,
  getVehicleEvents,
  runCommandRequest,
  runProviderSmokeTestRequest,
  updateVehicleStateRequest,
};

async function init() {
  try {
    const payload = await getInitialState();
    state.scenarios = payload.scenarios;
    state.demoSteps = payload.demo_steps || [];
    state.users = payload.users;
    renderVehicle(nodes, payload.vehicle_state);
    renderAutoEvents(nodes, payload.auto_events || [], payload.auto_event_rules || []);
    renderOfflineEvaluation(nodes, payload.offline_evaluation);
    renderAcceptance(nodes, payload.acceptance);
    renderProviders(nodes, payload.providers);
    renderUsers(nodes, state);
    const deps = buildDeps();
    renderScenarioButtons(nodes, state, (network) => setNetwork(nodes, state, network), () => deps.renderers.runCommand());
    renderDemoSteps(nodes, state, (network) => setNetwork(nodes, state, network), () => deps.renderers.runCommand());
    bindEvents(deps);
    deps.renderers.startVehicleEventPolling();
  } catch (error) {
    renderCommandError(nodes, error, buildDeps().renderers);
  }
}

function buildDeps() {
  const deps = {
    nodes,
    state,
    api,
    renderers: {},
  };
  deps.renderers = createRenderers(deps);
  return deps;
}

function createRenderers(deps) {
  return {
    runCommand: () => import("./js/events.js").then((module) => module.runCommand(deps)),
    startVehicleEventPolling: () => import("./js/events.js").then((module) => module.startVehicleEventPolling(deps)),
  };
}

init();
```

If dynamic imports make the dependency shape harder to test, use static imports instead and keep the same behavior. The final `app.js` must include imports from `./js/api.js` and `./js/events.js`.

- [ ] **Step 3: Update `index.html`**

Change:

```html
<script src="/app.js"></script>
```

to:

```html
<script type="module" src="/app.js"></script>
```

- [ ] **Step 4: Run frontend tests**

Run:

```powershell
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests\test_web_demo_frontend_logic.py -q
```

Expected: PASS.

---

### Task 6: Full Verification and Local Web Smoke Test

**Files:**
- No planned source edits unless tests reveal issues.

- [ ] **Step 1: Run full test suite**

Run:

```powershell
$basetemp = Join-Path (Get-Location) ("pytest-cache-files-" + [guid]::NewGuid().ToString("N")); & "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests --basetemp=$basetemp -q
```

Expected: all tests pass. Current baseline before this refactor is `224 passed, 124 subtests passed`.

- [ ] **Step 2: Restart local Web demo**

Run with escalation if needed:

```powershell
$existing = netstat -ano | Select-String ':8031' | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^\d+$' -and $_ -ne '0' } | Select-Object -Unique
foreach ($pidText in $existing) { Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -ArgumentList @("-m","web_demo.server","--host","127.0.0.1","--port","8031") -WorkingDirectory "E:\claudeCode\weilaiAgent" -WindowStyle Hidden
```

Expected: `http://127.0.0.1:8031/` loads.

- [ ] **Step 3: API smoke test critical flows**

Run:

```powershell
@'
import json
import time
import urllib.request

base = 'http://127.0.0.1:8031'

def post(path, payload):
    data = json.dumps(payload, ensure_ascii=True).encode('ascii')
    req = urllib.request.Request(base + path, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

time.sleep(2)
normal = post('/api/run', {'content': '\u5bfc\u822a\u53bb\u851a\u6765\u4e2d\u5fc3', 'user_id': 'user_001', 'network': 'ONLINE'})
post('/api/vehicle-state', {'battery_percent': 8})
charge = post('/api/run', {'content': '\u5bfc\u822a\u53bb\u851a\u6765\u4e2d\u5fc3', 'user_id': 'user_001', 'network': 'ONLINE'})
post('/api/vehicle-state', {'battery_percent': 4})
heat = post('/api/run', {'content': '\u6253\u5f00\u5ea7\u6905\u52a0\u70ed', 'user_id': 'user_001', 'network': 'OFFLINE'})
post('/api/vehicle-state', {'battery_percent': 35})
print(json.dumps({
    'normal_navigation': normal['result']['status'],
    'critical_navigation': charge['result']['status'],
    'critical_heat': heat['result']['status'],
}, ensure_ascii=False, indent=2))
'@ | & "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -
```

Expected:

```json
{
  "normal_navigation": "EXECUTED",
  "critical_navigation": "NEEDS_CHARGE_CONFIRMATION",
  "critical_heat": "BLOCKED"
}
```

- [ ] **Step 4: Commit implementation**

Run:

```powershell
git status --short
git add web_demo/static/app.js web_demo/static/index.html web_demo/static/js tests/test_web_demo_frontend_logic.py
git commit -m "refactor: modularize web demo frontend"
```

---

## Self-Review

- Spec coverage: module layout, API extraction, renderers, event orchestration, ES module loading, tests, and smoke checks are covered.
- Placeholder scan: no incomplete placeholder instructions remain.
- Scope check: the plan is limited to frontend modularization and does not add product behavior.
- Type consistency: module names and exported function names are consistent across tasks.
