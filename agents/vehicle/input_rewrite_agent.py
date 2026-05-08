import json
import os
from dataclasses import asdict, dataclass

from core.constants import CommandType
from llm.local_provider import create_local_llm_provider
from memory.local_agent_context_manager import DEFAULT_SESSION_ID, LocalAgentContextManager


@dataclass(frozen=True)
class InputRewriteResult:
    raw_input: str
    rewritten_input: str
    intent_hint: CommandType = CommandType.UNKNOWN
    slots: dict = None
    confidence: float = 0.0
    needs_clarification: bool = False
    reason: str = ""
    source: str = "rule"
    memory_used: list = None

    def to_dict(self):
        payload = asdict(self)
        payload["intent_hint"] = self.intent_hint.value
        payload["slots"] = self.slots or {}
        payload["memory_used"] = self.memory_used or []
        return payload


class InputRewriteAgent:
    role_name = "输入重写 Agent"

    def __init__(
        self,
        local_llm_provider=None,
        context_manager=None,
        enable_llm_rewrite=None,
        agent_id: str = "input_rewrite",
        memory_source_agent_id: str = "local_intent",
        session_id: str = DEFAULT_SESSION_ID,
    ):
        self.local_llm_provider = local_llm_provider or create_local_llm_provider()
        self.context_manager = context_manager or LocalAgentContextManager()
        self.agent_id = agent_id
        self.memory_source_agent_id = memory_source_agent_id
        self.session_id = session_id
        self.enable_llm_rewrite = (
            self._default_llm_enabled()
            if enable_llm_rewrite is None
            else bool(enable_llm_rewrite)
        )

    def rewrite(
        self,
        raw_input: str,
        user_id: str = "anonymous",
        preference_state=None,
        vehicle_state=None,
    ) -> InputRewriteResult:
        context = self.build_rewrite_context(
            raw_input,
            user_id=user_id,
            preference_state=preference_state,
            vehicle_state=vehicle_state,
        )
        fallback = self._rule_rewrite(raw_input, context)
        if not self.enable_llm_rewrite:
            return fallback

        try:
            raw = self.local_llm_provider.generate(
                system_prompt=(
                    "你是车载端离线小参数 LLM 的输入重写 Agent。"
                    "你只能基于本地记忆、车辆状态、用户偏好和当前指令做理解标准化。"
                    "不要生成任何可执行危险车控指令，不要丢失城市、地点、数值和否定词。"
                    "只输出 JSON。"
                ),
                user_prompt=(
                    f"原始用户输入：{raw_input}\n"
                    "请输出字段：rewritten_input, intent_hint, slots, confidence, "
                    "needs_clarification, reason, memory_used。"
                ),
                context=context,
            )
            return self._result_from_llm(raw_input, raw, fallback)
        except Exception:
            return fallback

    def build_rewrite_context(
        self,
        raw_input: str,
        user_id: str,
        preference_state=None,
        vehicle_state=None,
    ) -> dict:
        memory = self.context_manager.snapshot(
            user_id,
            agent_id=self.memory_source_agent_id,
            session_id=self.session_id,
        )
        return {
            "memory_scope": "agent_local",
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "user_id": user_id,
            "raw_input": raw_input,
            "memory_source_agent_id": self.memory_source_agent_id,
            "summary": memory.get("summary", ""),
            "recent_turns": memory.get("recent_turns", []),
            "preference_state": preference_state or {},
            "vehicle_state": vehicle_state or {},
            "rewrite_policy": {
                "preserve_raw_input": True,
                "rewrite_is_advisory": True,
                "safety_must_check_raw_and_rewritten": True,
            },
        }

    def _rule_rewrite(self, raw_input: str, context: dict) -> InputRewriteResult:
        text = _clean(raw_input)
        recent_destination = _last_navigation_destination(context.get("recent_turns", []))
        if recent_destination and _is_deictic_destination_reference(text):
            return InputRewriteResult(
                raw_input=raw_input,
                rewritten_input=f"导航去{recent_destination}",
                intent_hint=CommandType.NAVIGATION,
                slots={"destination": recent_destination},
                confidence=0.82,
                reason="根据最近一次导航目的地补全指代表达",
                source="rule",
                memory_used=["recent_turns"],
            )

        if _looks_like_navigation_without_prefix(text):
            destination = _strip_go_prefix(text)
            return InputRewriteResult(
                raw_input=raw_input,
                rewritten_input=f"导航去{destination}",
                intent_hint=CommandType.NAVIGATION,
                slots={"destination": destination},
                confidence=0.72,
                reason="补全导航动作词",
                source="rule",
                memory_used=[],
            )

        return InputRewriteResult(
            raw_input=raw_input,
            rewritten_input=raw_input,
            intent_hint=CommandType.UNKNOWN,
            slots={},
            confidence=0.5,
            reason="无需重写",
            source="rule",
            memory_used=[],
        )

    def _result_from_llm(
        self,
        raw_input: str,
        raw_output: str,
        fallback: InputRewriteResult,
    ) -> InputRewriteResult:
        payload = _extract_json(raw_output)
        rewritten = _clean(payload.get("rewritten_input", "")) or fallback.rewritten_input
        intent_hint = _command_type(payload.get("intent_hint"), fallback.intent_hint)
        confidence = _bounded_float(payload.get("confidence"), fallback.confidence)
        return InputRewriteResult(
            raw_input=raw_input,
            rewritten_input=rewritten,
            intent_hint=intent_hint,
            slots=payload.get("slots") if isinstance(payload.get("slots"), dict) else fallback.slots,
            confidence=confidence,
            needs_clarification=bool(payload.get("needs_clarification", False)),
            reason=str(payload.get("reason") or fallback.reason or ""),
            source="local_llm",
            memory_used=_string_list(payload.get("memory_used")) or fallback.memory_used,
        )

    def _default_llm_enabled(self) -> bool:
        raw = os.getenv("ENABLE_LOCAL_LLM_INPUT_REWRITE")
        if raw is not None:
            return raw.strip() == "1"
        provider_name = getattr(
            self.local_llm_provider,
            "provider_name",
            self.local_llm_provider.__class__.__name__,
        )
        return provider_name not in {"mock", "mock_local", "MockLocalLLMProvider"}


def normalize_rewrite_result(value, raw_input: str = "") -> InputRewriteResult:
    if isinstance(value, InputRewriteResult):
        return value
    if isinstance(value, dict):
        return InputRewriteResult(
            raw_input=value.get("raw_input") or raw_input,
            rewritten_input=value.get("rewritten_input") or raw_input,
            intent_hint=_command_type(value.get("intent_hint"), CommandType.UNKNOWN),
            slots=value.get("slots") if isinstance(value.get("slots"), dict) else {},
            confidence=_bounded_float(value.get("confidence"), 0.0),
            needs_clarification=bool(value.get("needs_clarification", False)),
            reason=str(value.get("reason") or ""),
            source=str(value.get("source") or "unknown"),
            memory_used=_string_list(value.get("memory_used")),
        )
    return InputRewriteResult(raw_input=raw_input, rewritten_input=raw_input)


def _extract_json(raw_output: str) -> dict:
    text = (raw_output or "").strip()
    if not text:
        raise ValueError("empty rewrite output")
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("rewrite output must be an object")
    return payload


def _last_navigation_destination(turns) -> str:
    for turn in reversed(list(turns or [])):
        if turn.get("command_type") != CommandType.NAVIGATION.value:
            continue
        destination = _extract_destination(turn.get("user_input", ""))
        if destination:
            return destination
    return ""


def _extract_destination(content: str) -> str:
    text = _clean(content)
    for prefix in ("导航去", "导航到", "我要去", "去", "到"):
        if text.startswith(prefix):
            return _clean(text[len(prefix) :])
    return ""


def _is_deictic_destination_reference(text: str) -> bool:
    return any(marker in text for marker in ("刚才", "上次", "那个地方", "那里", "那边"))


def _looks_like_navigation_without_prefix(text: str) -> bool:
    if text.startswith(("导航去", "导航到")):
        return False
    if text in {"回家", "我要回家", "去公司", "去家里"}:
        return True
    return text.startswith(("去", "到")) and len(text) > 1


def _strip_go_prefix(text: str) -> str:
    for prefix in ("我要去", "去", "到"):
        if text.startswith(prefix):
            return _clean(text[len(prefix) :])
    return text


def _command_type(value, default: CommandType) -> CommandType:
    if isinstance(value, CommandType):
        return value
    normalized = str(value or "").strip().upper()
    for command_type in CommandType:
        if command_type.value == normalized:
            return command_type
    return default


def _bounded_float(value, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return min(1.0, max(0.0, number))


def _string_list(value) -> list:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _clean(value: str) -> str:
    return str(value or "").strip().strip("。！？?! ")
