# Destination Clarification Loop Design

**Goal:** Turn fuzzy navigation inputs from provider errors into a normal product state that asks the user to clarify before routing.

**Context:** The current system already blocks several fuzzy destinations before AMap routing, and it also rejects low-confidence AMap geocode results after provider response. The missing product layer is a first-class clarification flow: the backend should return `NEEDS_CLARIFICATION`, the web demo should render it as a question, and a follow-up user answer should resolve the pending navigation task.

## Product Principle

The system should not treat “map provider returned a coordinate” as proof that the destination is valid. For navigation, a result is executable only when the user intent, destination slots, and candidate confidence jointly support one unique target.

Fuzzy inputs are not failures. They are normal dialogue states.

Examples:

- `导航去北京` should ask for a concrete place in Beijing.
- `导航去高老庄` should ask for more location detail.
- `导航去霓虹蔚来中心` should ask which city or store the user means.
- `导航去北京蔚来中心` can execute after geocode quality validation.

## State Model

Add a new execution status:

```text
NEEDS_CLARIFICATION
```

This is distinct from:

- `BLOCKED`: unsafe or unknown command that should not continue.
- `FALLBACK`: offline local execution.
- `EXECUTED`: a completed action.

Clarification is allowed and safe, but incomplete.

## Data Contract

Introduce a structured clarification payload on `ExecutionResult`.

```python
clarification = {
    "type": "destination",
    "query": "高老庄",
    "reason": "unclear_destination",
    "question": "我还不能确认唯一目的地。请补充城市、商圈、门店或完整地址。",
    "suggestions": [
        "导航去北京东方广场蔚来中心",
        "导航去上海松江印象城蔚来中心"
    ],
    "candidates": []
}
```

When provider-backed candidates are available later, candidates should use a stable schema:

```python
candidate = {
    "id": "amap:121.222719,31.062206",
    "name": "蔚来中心(上海松江印象城)",
    "formatted_address": "上海市松江区蔚来中心(上海松江印象城)",
    "gps": "121.222719,31.062206",
    "source": "amap_geocode",
    "confidence": 0.86,
    "distance_km": 38.0
}
```

## Backend Flow

The route should become:

```text
LocalIntentAgent
-> SafetyAgent
-> DestinationResolver / ClarificationPolicy
-> if needs clarification: return NEEDS_CLARIFICATION
-> else Cloud/LangGraph route planning
-> provider quality validation
-> final decision
```

The pre-routing clarification gate should run before `GlobalDispatchAgent.dispatch()` for navigation and charge planning commands that require a concrete destination. This avoids invoking LangGraph, ecology, route planning, geocode, map route, or DeepSeek for a task that is not executable yet.

The low-confidence geocode validation remains as a second safety net after provider response.

## Follow-Up Handling

The first implementation should support a simple follow-up pattern without adding a large conversation engine.

Store pending clarification in local context:

```python
pending_clarification = {
    "request_id": "...",
    "type": "destination",
    "original_content": "导航去北京",
    "query": "北京",
    "command_type": "NAVIGATION"
}
```

If the next user input looks like a destination refinement, combine it with the original task:

- Previous: `导航去北京`
- Next: `东方广场蔚来中心`
- Reconstructed command: `导航去北京东方广场蔚来中心`

If the user switches topics, clear the pending clarification and process the new input normally.

## Web Demo Behavior

The web UI should render clarification as a normal result card, not as a red provider failure.

Expected UI:

- Status badge: `NEEDS_CLARIFICATION`
- Title: `需要确认目的地`
- Message: user-friendly question
- Suggestions: clickable prompt chips
- Runtime trace: `LocalIntentAgent -> GlobalSafetyDispatchAgent -> DestinationClarification`
- Route summary: empty
- Provider trace: empty, because no map provider was called

If the user clicks a suggestion or types a refinement, the input box should be filled or submitted as the next command.

## Error Handling

Use errors only for real failures:

- malformed JSON
- provider timeout
- provider response error
- LLM generation failure

Do not use `502` for known clarification states. `/api/run` should return HTTP `200` with `result.status = NEEDS_CLARIFICATION`.

Provider low-confidence errors can still be converted to `NEEDS_CLARIFICATION` if the system can ask a useful question. If the provider is unavailable, keep the existing provider error behavior.

## Testing Plan

Unit tests:

- `DestinationResolver` returns clarification payload for broad regions and unclear chain POIs before geocoder call.
- `VehicleCoreService` returns `ExecutionStatus.NEEDS_CLARIFICATION` without calling cloud agent.
- `web_demo.app_model.run_command()` returns a clarification payload with empty route summary.
- follow-up refinement reconstructs a concrete navigation command.

Integration tests:

- `导航去北京` -> `NEEDS_CLARIFICATION`
- follow-up `东方广场蔚来中心` -> `EXECUTED`
- `导航去霓虹蔚来中心` -> `NEEDS_CLARIFICATION`
- `导航去北京蔚来中心` -> `EXECUTED`
- `关闭AEB` remains `BLOCKED`

Web tests:

- frontend renders clarification card instead of provider error.
- suggestion chips populate or submit the command.
- Agent trace shows clarification gate and no provider route tools.

## Implementation Boundaries

Initial implementation should avoid a full dialogue manager. It should add only enough context handling to continue a pending destination clarification.

Do not add a new external provider for candidate search in the first pass. Candidate lists can start as empty or suggestion-based. Provider-backed candidate ranking can be a later enhancement.

Do not change the existing DeepSeek prompt contract unless needed for final wording. Clarification should be deterministic and local.

## Interview Story

This upgrade demonstrates product judgment:

> “I realized fuzzy navigation should not be modeled as an API failure. It is a normal multi-turn interaction state. So I introduced a clarification gate before cloud routing. That keeps the map and LLM from fabricating certainty, improves safety, and gives the user a recoverable next step.”

