# Agent Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compatible structured schema layer for Agent messages, traces, provider outputs, and execution results.

**Architecture:** Add `core/agent_schema.py` as a thin protocol layer. Existing `Message` and `ExecutionResult` keep their current fields and gain conversion helpers, so current service and frontend code remain compatible.

**Tech Stack:** Python dataclasses, existing enums in `core.constants`, existing `TraceEvent`.

---

### Task 1: Schema Frames

**Files:**
- Create: `core/agent_schema.py`
- Test: `tests/test_agent_schema.py`

- [x] Define `IntentFrame`, `VehicleStateFrame`, `ProviderResultFrame`, `AgentTraceFrame`, and `ExecutionResultFrame`.
- [x] Give every frame a `to_dict()` method.
- [x] Normalize enum values through a shared helper.

### Task 2: Compatibility Conversions

**Files:**
- Modify: `core/message.py`
- Modify: `core/vehicle_core_service.py`
- Test: `tests/test_agent_schema.py`

- [x] Add `Message.to_dict()`.
- [x] Add `Message.to_intent_frame(...)`.
- [x] Add `ExecutionResult.to_frame()` and `ExecutionResult.to_dict()`.

### Task 3: Verification

**Files:**
- Test: `tests/test_agent_schema.py`

- [x] Verify message conversion.
- [x] Verify vehicle state conversion.
- [x] Verify trace/provider result conversion.
- [x] Verify execution result conversion.
- [x] Run targeted tests and full regression.
