# Engineering Hardening Design

**Goal:** Improve the existing automotive Multi-Agent project by tightening module boundaries, state modeling, destination ambiguity handling, and acceptance assets without disrupting the current runnable demo.

**Primary outcome:** The project should become easier to explain in interviews and easier to extend in code. The next implementation should reduce obvious coupling in intent recognition and destination resolution, add missing business semantics such as `INFO_QUERY`, and update validation artifacts to match the current baseline.

## Current Context

The project is currently on branch `codex/destination-clarification-loop`. The latest implementation added `NEEDS_CLARIFICATION`, pending destination clarification storage, web clarification rendering, and tests. The full suite passed with `171 passed, 1 warning`.

The strongest remaining engineering issues are concentrated in a few files:

- `agents/vehicle/local_intent_agent.py` is doing intent framing, rule matching, slot extraction, risk signal collection, LLM fallback, context packaging, and result recording.
- `providers/destination_resolver.py` is doing query extraction, query normalization, known-destination lookup, ambiguity policy, and geocoder handoff.
- `web_demo/static/app.js` and `web_demo/static/styles.css` are large, but frontend decomposition is not the first priority unless new UI work forces it.
- Acceptance artifacts need to catch up with the new baseline and new clarification behavior.

## Scope

This optimization should prioritize engineering quality, not a broad feature sprint. The work should focus on four packages.

## Package 1: Intent Layer Boundary

Keep `LocalIntentAgent` as the public facade so existing tests and callers continue to work.

Extract clear internal modules:

- `IntentFrame`: stable dataclass for command type, slots, confidence, evidence, risk signals, and reason.
- `SlotExtractor`: extracts structured slots such as navigation destination text, cabin temperature, seat heat action, and info-query topic.
- `IntentRuleEngine`: deterministic rules for navigation, car control, charge planning, personalization, info query, and unknown.
- `IntentEvidenceCollector`: optional helper for matched keywords, negation signals, and risk signals.

`LocalIntentAgent` should become an orchestrator:

```text
input
-> SlotExtractor
-> IntentRuleEngine
-> optional local LLM fallback
-> IntentFrame
```

The existing API should remain:

- `recognize` returns `CommandType`.
- `analyze` returns `IntentFrame`.
- `retrieve_context` keeps the current RAG-style context retrieval contract.
- `build_local_llm_context` keeps the current local context package contract.
- `record_result` keeps the current local memory update contract.

Target: reduce `local_intent_agent.py` from a mixed 480+ line file into a smaller facade while moving pure logic into isolated, tested modules.

## Package 2: Destination Layer Boundary

Keep `resolve_destination` and `resolve_destination_detail` as compatibility functions.

Extract destination concepts:

- `DestinationResolution`: executable destination, already resolved to a single target.
- `DestinationCandidate`: possible target with name, formatted address, gps, source, confidence, distance, and reason.
- `DestinationClarification`: structured domain object used to produce `NEEDS_CLARIFICATION`.
- `DestinationQuery`: extracted and normalized destination query.
- `ClarificationPolicy`: deterministic ambiguity rules.
- `DestinationResolver`: orchestrates known lookup, clarification policy, geocoder, and candidate validation.

The resolver should distinguish:

- Executable unique target.
- Needs clarification before provider call.
- Provider returned low-confidence result.
- Provider unavailable or failed.

Candidate support should be introduced as a contract first. It does not need a full provider-backed POI selection UI in this engineering pass, but backend objects and tests should make candidate-based behavior possible.

Examples:

- `导航去北京` -> `NEEDS_CLARIFICATION`, reason `broad_region`.
- `导航去霓虹蔚来中心` -> `NEEDS_CLARIFICATION`, reason `unknown_chain_poi_qualifier`.
- `导航去121.48,31.23` -> executable explicit GPS.
- `导航去北京东方广场蔚来中心` -> provider-backed route planning if provider succeeds.

## Package 3: Business State Semantics

Add `CommandType.INFO_QUERY`.

This separates informational questions from unknown or unsafe commands.

Examples:

- `AEB是什么` -> `INFO_QUERY`, `SAFE`.
- `讲一下制动距离` -> `INFO_QUERY`, `SAFE`.
- `关闭AEB` -> `CAR_CONTROL`, `DANGEROUS`, `BLOCKED`.
- `立即刹车` -> `CAR_CONTROL`, `DANGEROUS`, `BLOCKED`.

Handling policy:

- `INFO_QUERY` should not call vehicle control.
- `INFO_QUERY` can use RAG/LLM explanation if online.
- Offline behavior may return a local knowledge explanation or local fallback.
- It should be represented as a normal command type, not as `UNKNOWN`.

Do not add a second clarification execution status. The existing `ExecutionStatus.NEEDS_CLARIFICATION` is sufficient and clearer than adding a parallel `CLARIFICATION` status.

## Package 4: Acceptance And Interview Assets

Update acceptance assets after code stabilizes.

Acceptance should include:

- Unit test count from the actual test run.
- Clarification scenarios.
- `INFO_QUERY` scenarios.
- Provider confidence/low-confidence behavior.
- Frontend clarification rendering.
- Data feedback behavior: clarification does not update preference.

Documents to update or add:

- `reports/acceptance_report.md`
- `docs/acceptance-and-interview-review.md`
- `docs/agent-roles-and-workflows.md`
- `docs/architecture-diagram.md` if state flow changes
- A short engineering note explaining why state modeling and module boundaries were improved

## Non-Goals

This pass should not:

- Replace the whole frontend architecture.
- Add a full production dialogue manager.
- Add Milvus, MQTT, Docker, or local model deployment.
- Force every Agent to call an LLM.
- Build a complete map candidate selection UI unless it is needed to support a small backend candidate contract.
- Remove existing public APIs that tests and demo code already depend on.

## Testing Strategy

Use TDD for every behavior change.

Focused tests:

- `test_intent_agent.py`: `INFO_QUERY`, negation, meta questions, dangerous control separation.
- New or updated intent module tests for `SlotExtractor` and `IntentRuleEngine`.
- `test_destination_resolver.py`: query extraction, normalization, clarification policy, candidate object shape.
- `test_clarification_loop.py`: existing clarification and follow-up behavior remains intact.
- `test_input_matrix.py`: broader service-level matrix for info query, clarification, GPS, car control, charge plan, and safety.
- `test_web_demo_app_model.py`: web payload semantics for `INFO_QUERY` and clarification.
- `test_acceptance_runner.py`: acceptance report includes current baseline and new scenarios.

Full verification:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$basetemp = Join-Path (Get-Location) (".test_runtime\pytest-" + [guid]::NewGuid().ToString("N"))
& "C:\Users\scyqw3\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests --basetemp=$basetemp -p no:cacheprovider
```

Expected: all tests pass. The existing LangGraph `allowed_objects` warning is acceptable unless new warnings appear.

## Implementation Order

1. Add `INFO_QUERY` tests and semantics while keeping the existing agent facade.
2. Extract slot extraction and deterministic intent rules behind `LocalIntentAgent`.
3. Extract destination models and clarification policy behind compatibility functions.
4. Add candidate data contract tests and minimal backend candidate payload support.
5. Update web/app model only where the new state or candidate contract requires it.
6. Update acceptance scripts, reports, and interview docs.

## Success Criteria

- Existing demo scenarios still run.
- `AEB是什么` is no longer `UNKNOWN`; it becomes `INFO_QUERY`.
- Dangerous controls remain blocked before cloud dispatch.
- Fuzzy destinations remain `NEEDS_CLARIFICATION`.
- `LocalIntentAgent` and `destination_resolver.py` become facades rather than mixed logic buckets.
- Candidate-related structures exist and are tested even if full POI UI remains a later enhancement.
- Acceptance report reflects the actual test baseline after the change.
- Full test suite passes.

## Interview Story

This optimization should support the following interview explanation:

> I did not just add more if-else rules. I separated command semantics from execution status, and separated intent framing from slot extraction and clarification policy. That made the system easier to test, safer for vehicle commands, and more realistic for navigation, where ambiguity is a normal dialogue state rather than an API failure.
