# Engineering Hardening First Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the project look and behave more like a team-deliverable engineering asset without changing the current demo behavior.

**Architecture:** Add small boundary modules first instead of rewriting business logic. Configuration is centralized behind `AppSettings`; provider failures are normalized behind `ProviderError`; CI runs deterministic offline checks; docs explain the new engineering baseline.

**Tech Stack:** Python dataclasses, stdlib `os`, stdlib `urllib`, pytest, GitHub Actions, existing PowerShell scripts.

---

### Task 1: Centralized Settings

**Files:**
- Create: `config/settings.py`
- Modify: `providers/factory.py`
- Test: `tests/test_settings.py`

- [ ] **Step 1: Add tests for settings defaults and env override**

Create tests that verify `AppSettings.from_env()` preserves current defaults and reads existing environment names such as `ENABLE_LANGGRAPH`, `DEEPSEEK_MODEL`, `AMAP_API_KEY`, `USE_OPEN_METEO`, and `USE_OPENCHARGEMAP`.

- [ ] **Step 2: Implement `AppSettings`**

Create a dataclass with fields for LangGraph, DeepSeek, local LLM, AMap, Baidu, Open-Meteo, OpenChargeMap, and provider timeout/retry defaults.

- [ ] **Step 3: Route provider factory through settings**

Change `providers/factory.py` to call `get_settings()` once per factory function instead of reading `os.getenv()` directly.

- [ ] **Step 4: Run focused tests**

Run `pytest tests/test_settings.py tests/test_offline_providers.py -q`.

### Task 2: Provider Error Boundary

**Files:**
- Create: `providers/errors.py`
- Create: `providers/http.py`
- Modify: `providers/amap_route_provider.py`
- Modify: `providers/amap_poi_provider.py`
- Modify: `providers/amap_geocode_provider.py`
- Modify: `providers/open_meteo_weather_provider.py`
- Modify: `providers/open_charge_map_provider.py`
- Test: `tests/test_provider_errors.py`

- [ ] **Step 1: Add tests for normalized provider errors**

Cover HTTP failure wrapping, JSON parse failure wrapping, AMap status failure, and empty route path failure.

- [ ] **Step 2: Add `ProviderError` family**

Define `ProviderError`, `ProviderTimeoutError`, `ProviderUnavailableError`, and `ProviderBadResponseError` with `provider`, `operation`, `code`, `retryable`, and optional `details`.

- [ ] **Step 3: Add shared JSON transport**

Create `get_json()` with timeout, one retry for retryable network failures, JSON parsing, and normalized exceptions.

- [ ] **Step 4: Migrate first providers**

Start with AMap Route and Open-Meteo because they affect the main demo path.

- [ ] **Step 5: Run focused provider tests**

Run `pytest tests/test_provider_errors.py tests/test_offline_providers.py -q`.

### Task 3: Minimal CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`

- [ ] **Step 1: Add offline deterministic GitHub Actions workflow**

The workflow installs requirements and runs pytest with cache disabled. It must not require API keys.

- [ ] **Step 2: Document CI behavior**

Update README to explain that real Provider smoke tests are local/manual, while CI runs deterministic offline tests.

### Task 4: Delivery Hygiene Notes

**Files:**
- Modify: `.gitignore`
- Modify: `docs/project-challenges-and-breakthroughs.md`

- [ ] **Step 1: Ensure generated report/cache paths are ignored**

Add `.test_runtime/reports/`, `reports/browser_qa/`, and generated web demo temp patterns if missing.

- [ ] **Step 2: Record engineering-hardening decision**

Add a short section explaining why configuration, provider error normalization, and CI were prioritized before larger schema migration.

### Task 5: Verification

**Files:**
- No new files unless verification output requires docs updates.

- [ ] **Step 1: Run focused tests**

Run focused tests for settings and providers.

- [ ] **Step 2: Run broader regression subset**

Run the current stable subset covering cloud runtime trace, LangGraph workflow, web app model, web frontend logic, and safety dispatch.

- [ ] **Step 3: Review git status**

Confirm changes are scoped and ready to group into commits.
