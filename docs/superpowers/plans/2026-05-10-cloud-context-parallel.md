# Cloud Context Parallelization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make cloud context collection execute as a real parallel fan-out and show that parallel semantics in the web observability panel.

**Architecture:** `GlobalDispatchAgent` keeps ownership of orchestration, but profile, knowledge, route preference, and ecology are gathered through one `context_parallel` fan-out node before trip planning. The web trace reads graph metadata and marks the corresponding Agent rows as "parallel collection", while final LLM summarization is shown under a dedicated decision Agent row instead of the dispatch entry row.

**Tech Stack:** Python standard library `concurrent.futures`, existing LangGraph wrapper, vanilla ES modules frontend, pytest.

---

### Task 1: Backend Parallel Context Fan-Out

**Files:**
- Modify: `agents/orchestrator/global_dispatch_agent.py`
- Modify: `workflow/cloud_graph.py`
- Test: `tests/test_langgraph_workflow.py`
- Test: `tests/test_cloud_runtime_trace.py`

- [ ] Add a failing test that expects graph path `context_parallel -> trip_plan -> decision -> assemble`.
- [ ] Add graph metadata `parallel_groups` with nodes `profile`, `knowledge`, `route_preference`, and `ecology` for navigation tasks.
- [ ] Implement `GlobalDispatchAgent._graph_context_parallel()` with `ThreadPoolExecutor`, collecting independent context tools in parallel and appending deterministic trace records afterward.
- [ ] Change the LangGraph wrapper to use a `context_parallel` node before route planning or decision.

### Task 2: Frontend Parallel Trace Display

**Files:**
- Modify: `web_demo/static/js/renderers/result.js`
- Modify: `web_demo/static/js/renderers/trace.js`
- Modify: `web_demo/static/styles.css`
- Test: `tests/test_web_demo_frontend_logic.py`

- [ ] Pass graph metadata into `renderAlignedTrace`.
- [ ] Mark agent rows mapped to graph `parallel_groups` as parallel rows and add a "并行收集" badge.
- [ ] Move `decision.summarize` rendering under `CloudDecisionAgent`.
- [ ] Render graph path as `并行[...] -> trip_plan -> decision -> assemble`.

### Task 3: Cache Bust And Verify

**Files:**
- Modify: `web_demo/static/index.html`
- Modify: `web_demo/static/app.js`
- Modify: frontend module import query strings
- Test: `tests/test_web_demo_markup.py`
- Test: `tests/test_web_demo_frontend_logic.py`

- [ ] Bump static asset version to `parallel-context-v1-20260510`.
- [ ] Run focused backend/frontend tests.
- [ ] Restart the local web server on port 8031.
