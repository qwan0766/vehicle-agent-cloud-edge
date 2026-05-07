import os

from agents.vehicle.intent.models import IntentFrame
from agents.vehicle.intent.rule_engine import IntentRuleEngine
from core.constants import CommandType
from llm.local_provider import create_local_llm_provider
from memory.local_agent_context_manager import LocalAgentContextManager
from rag.documents import INTENT_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class LocalIntentAgent:
    role_name = "本地意图识别 Agent"

    def __init__(
        self,
        llm_client=None,
        local_llm_provider=None,
        enable_llm_fallback=None,
        context_manager=None,
        agent_id: str = "local_intent",
        session_id: str = "default",
    ):
        self.retriever = SimpleRetriever(INTENT_DOCUMENTS)
        self.rule_engine = IntentRuleEngine(retriever=self.retriever)
        self.local_llm_provider = (
            local_llm_provider or llm_client or create_local_llm_provider()
        )
        self.llm_client = self.local_llm_provider
        self.context_manager = context_manager or LocalAgentContextManager()
        self.agent_id = agent_id
        self.session_id = session_id
        self.enable_llm_fallback = (
            os.getenv("ENABLE_LLM_INTENT_FALLBACK") == "1"
            if enable_llm_fallback is None
            else enable_llm_fallback
        )

    def recognize(
        self,
        user_input: str,
        user_id: str = "anonymous",
        preference_state=None,
        vehicle_state=None,
    ) -> CommandType:
        return self.analyze(
            user_input,
            user_id=user_id,
            preference_state=preference_state,
            vehicle_state=vehicle_state,
        ).command_type

    def analyze(
        self,
        user_input: str,
        user_id: str = "anonymous",
        preference_state=None,
        vehicle_state=None,
    ) -> IntentFrame:
        rule_frame = self.rule_engine.analyze(user_input)
        if rule_frame.reason != "no_rule_match":
            return rule_frame

        results = self.retriever.search(user_input, top_k=1)
        if results and self._is_reliable_intent_match(user_input, results[0]):
            return self._frame(
                results[0].document.metadata["command_type"],
                confidence=min(0.82, 0.5 + results[0].score / 20),
                evidence=rule_frame.evidence,
                risk_signals=rule_frame.risk_signals,
                reason="reliable_retrieval_candidate",
            )
        if self.enable_llm_fallback:
            command_type = self._recognize_with_llm(
                user_input,
                user_id=user_id,
                preference_state=preference_state,
                vehicle_state=vehicle_state,
            )
            return self._frame(
                command_type,
                confidence=0.72 if command_type != CommandType.UNKNOWN else 0.2,
                evidence=rule_frame.evidence,
                risk_signals=rule_frame.risk_signals,
                reason="local_llm_fallback",
            )
        return self._frame(
            CommandType.UNKNOWN,
            confidence=0.2,
            evidence=rule_frame.evidence,
            risk_signals=rule_frame.risk_signals,
            reason="no_reliable_candidate",
        )

    def retrieve_context(self, user_input: str):
        return self.retriever.search(user_input, top_k=2)

    def build_local_llm_context(
        self,
        user_id: str,
        preference_state=None,
        current_input: str = "",
        vehicle_state=None,
    ):
        retrieved_context = [
            {
                "doc_id": item.document.doc_id,
                "text": item.document.text,
                "score": item.score,
                "matched_keywords": item.matched_keywords,
            }
            for item in self.retrieve_context(current_input)
        ]
        context = self.context_manager.build_local_llm_context(
            user_id=user_id,
            preference_state=preference_state,
            agent_id=self.agent_id,
            session_id=self.session_id,
            current_input=current_input,
            vehicle_state=vehicle_state,
            retrieved_context=retrieved_context,
        )
        return self._attach_local_llm_prompt(context)

    def record_result(self, result):
        snapshot = self.context_manager.record_result(
            result,
            agent_id=self.agent_id,
            session_id=self.session_id,
        )
        previous_context = result.local_context or {}
        for key in ("preference_state", "vehicle_state", "retrieved_context"):
            if key in previous_context:
                snapshot[key] = previous_context[key]
        if "window" in previous_context:
            snapshot["window"] = previous_context["window"]
        return self._attach_local_llm_prompt(
            snapshot,
            current_input=result.message.content,
        )

    def _recognize_with_llm(
        self,
        user_input: str,
        user_id: str = "anonymous",
        preference_state=None,
        vehicle_state=None,
    ) -> CommandType:
        context = self.build_local_llm_context(
            user_id=user_id,
            preference_state=preference_state,
            current_input=user_input,
            vehicle_state=vehicle_state,
        )
        raw = self.local_llm_provider.generate(
            system_prompt=context["local_llm"]["system_prompt"],
            user_prompt=context["local_llm"]["user_prompt"],
            context=context,
        ).strip()
        normalized = raw.split()[0].strip().upper()
        for command_type in CommandType:
            if command_type.value == normalized:
                return command_type
        return CommandType.UNKNOWN

    def _attach_local_llm_prompt(self, context, current_input: str = None):
        payload = dict(context or {})
        prompt_context = {
            key: value
            for key, value in payload.items()
            if key not in {"local_llm"}
        }
        current_input = current_input or payload.get("current_input", "")
        system_prompt = (
            "你是车载端离线小参数 LLM 的本地意图 Agent。"
            "你只能基于本地上下文、车辆状态、用户偏好和 RAG 召回结果工作。"
            "输出必须遵循任务要求，不能生成危险车辆控制指令。"
        )
        user_prompt = (
            f"用户指令：{current_input}\n"
            "请只输出以下枚举之一："
            "NAVIGATION、CAR_CONTROL、CHARGE_PLAN、PERSONALIZE、INFO_QUERY、UNKNOWN。"
        )
        prompt_preview = _compact_prompt_preview(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=prompt_context,
        )
        provider_name = getattr(
            self.local_llm_provider,
            "provider_name",
            self.local_llm_provider.__class__.__name__,
        )
        context_limit_tokens = int(
            getattr(
                self.local_llm_provider,
                "context_limit_tokens",
                window_value(payload, "context_limit_tokens", 7500),
            )
        )
        generation_buffer_tokens = int(
            getattr(
                self.local_llm_provider,
                "generation_buffer_tokens",
                window_value(payload, "generation_buffer_tokens", 500),
            )
        )
        max_output_tokens = int(
            getattr(self.local_llm_provider, "max_output_tokens", 128)
        )
        prompt_budget_tokens = max(0, context_limit_tokens - generation_buffer_tokens)
        estimated_prompt_tokens = _estimate_tokens(prompt_preview)
        window = dict(payload.get("window") or {})
        window["context_limit_tokens"] = context_limit_tokens
        window["generation_buffer_tokens"] = generation_buffer_tokens
        window["max_output_tokens"] = max_output_tokens
        window["prompt_budget_tokens"] = prompt_budget_tokens
        window["estimated_prompt_tokens"] = estimated_prompt_tokens
        window["over_budget"] = estimated_prompt_tokens > prompt_budget_tokens
        payload["window"] = window
        payload["local_llm"] = {
            "provider": provider_name,
            "model": getattr(self.local_llm_provider, "model", "local-model"),
            "runtime_role": "edge_local_agent",
            "context_policy": "single_agent_window_with_summary",
            "is_edge_simulation": provider_name == "edge_deepseek_sim",
            "agent_scope": f"{payload.get('agent_id', self.agent_id)}/"
            f"{payload.get('session_id', self.session_id)}",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "prompt_preview": prompt_preview,
        }
        return payload

    def _is_reliable_intent_match(self, user_input: str, result) -> bool:
        command_type = result.document.metadata["command_type"]
        if command_type == CommandType.CAR_CONTROL:
            return _contains_any(
                user_input,
                [
                    "座椅",
                    "加热",
                    "温度",
                    "空调",
                    "车窗",
                    "后备箱",
                    "雨刷",
                    "车灯",
                    "AEB",
                    "自动紧急制动",
                    "方向盘",
                ],
            )
        if command_type == CommandType.CHARGE_PLAN:
            return _contains_any(user_input, ["电量", "补能", "充电", "换电"])
        if command_type == CommandType.PERSONALIZE:
            return _contains_any(user_input, ["偏好", "用户画像", "个性化", "画像"])
        return True

    def _frame(
        self,
        command_type: CommandType,
        slots=None,
        confidence: float = 0.0,
        evidence=None,
        risk_signals=None,
        reason: str = "",
    ) -> IntentFrame:
        return IntentFrame(
            command_type=command_type,
            slots=slots or {},
            confidence=confidence,
            evidence=evidence or {"keyword_hits": [], "retrieval": []},
            risk_signals=risk_signals or [],
            reason=reason,
        )


def window_value(payload, key: str, default):
    try:
        return (payload.get("window") or {}).get(key, default)
    except AttributeError:
        return default


def _contains_any(content: str, keywords) -> bool:
    normalized = (content or "").lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _compact_prompt_preview(system_prompt: str, user_prompt: str, context: dict) -> str:
    return (
        f"{system_prompt}\n\n"
        f"{user_prompt}\n\n"
        f"上下文包：\n{_safe_json(context)}"
    )


def _safe_json(value) -> str:
    import json

    return json.dumps(value or {}, ensure_ascii=False, indent=2, default=str)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 2)
