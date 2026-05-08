# Delivery Demo Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a delivery-grade demo and acceptance loop for interview-ready project presentation.

**Architecture:** Keep the backend API stable and add a higher-level delivery check script that composes existing tests, static frontend checks, and API smoke scenarios. Extend existing demo steps with vehicle-state presets so the frontend can reproduce interview scenarios without manual context setup.

**Tech Stack:** Python standard library, pytest/unittest, existing `web_demo` HTTP API, native ES modules in `web_demo/static/js`.

---

### Task 1: Delivery Check Script

**Files:**
- Create: `scripts/run_delivery_check.py`
- Test: `tests/test_delivery_check.py`

- [ ] Add tests that verify the script renders a Markdown report with status, scenario rows, and frontend module check rows.
- [ ] Implement `scripts/run_delivery_check.py` with subprocess unit test execution, JS syntax check, app-model demo scenario checks, and report generation.
- [ ] Verify `python -m pytest tests/test_delivery_check.py -q` passes.

### Task 2: Demo Mode Vehicle Presets

**Files:**
- Modify: `web_demo/app_model.py`
- Modify: `web_demo/static/app.js`
- Modify: `web_demo/static/js/events.js`
- Modify: `web_demo/static/js/renderers/demo.js`
- Test: `tests/test_web_demo_app_model.py`
- Test: `tests/test_web_demo_frontend_logic.py`

- [ ] Update demo steps to cover normal navigation, fuzzy destination clarification, highway speed confirmation, urban speed block, and low-battery energy policy.
- [ ] Add `vehicle_state` presets to demo steps.
- [ ] Make frontend demo clicks apply vehicle state before running the command.
- [ ] Verify frontend logic tests assert demo state presets and async apply flow.

### Task 3: Delivery Documentation

**Files:**
- Modify: `docs/current-delivery-snapshot.md`
- Modify: `docs/final-interview-delivery.md`

- [ ] Update the current delivery snapshot with the latest test baseline and delivery-check command.
- [ ] Add a concise interview demo script with the five scenes and talking points.

### Task 4: Full Verification

**Commands:**
- `node --check` for all frontend JS files.
- `python -m pytest tests -q` with offline/mock provider env.
- `python scripts/run_delivery_check.py --skip-provider-smoke`.

- [ ] Confirm all checks pass.
- [ ] Restart `http://127.0.0.1:8031/`.
- [ ] Commit the completed work.
