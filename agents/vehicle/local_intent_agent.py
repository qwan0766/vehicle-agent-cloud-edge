import os
import re
from dataclasses import dataclass
from typing import Dict, List

from core.constants import CommandType
from data.knowledge_base import DANGEROUS_KEYWORDS, INTENT_KNOWLEDGE
from llm.local_provider import create_local_llm_provider
from memory.local_agent_context_manager import LocalAgentContextManager
from providers.destination_resolver import extract_destination_query, normalize_destination_query
from rag.documents import INTENT_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


@dataclass(frozen=True)
class IntentFrame:
    command_type: CommandType
    slots: Dict[str, object]
    confidence: float
    evidence: Dict[str, object]
    risk_signals: List[str]
    reason: str


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
        text = (user_input or "").strip()
        evidence = self._collect_evidence(text)
        risk_signals = self._collect_risk_signals(text)

        if not text:
            return self._frame(
                CommandType.UNKNOWN,
                confidence=0.0,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="empty_input",
            )

        for example, command_type in INTENT_KNOWLEDGE.items():
            if text == example:
                return self._frame(
                    command_type,
                    confidence=0.98,
                    evidence=evidence,
                    risk_signals=risk_signals,
                    reason="exact_builtin_example",
                )

        if _is_negated_or_meta_request(text):
            return self._frame(
                CommandType.UNKNOWN,
                confidence=0.25,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="negated_or_meta_request",
            )

        if _is_non_actionable_question(text) and not _is_charge_request(text):
            return self._frame(
                CommandType.UNKNOWN,
                confidence=0.35,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="non_actionable_question",
            )

        destination_query = extract_destination_query(text)
        if destination_query:
            return self._frame(
                CommandType.NAVIGATION,
                slots={
                    "raw_destination": destination_query,
                    "destination_query": normalize_destination_query(destination_query),
                },
                confidence=0.94,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="navigation_slot_extracted",
            )

        if _is_charge_request(text):
            return self._frame(
                CommandType.CHARGE_PLAN,
                confidence=0.9,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="charge_request_pattern",
            )

        if _is_personalize_request(text):
            return self._frame(
                CommandType.PERSONALIZE,
                confidence=0.9,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="personalize_request_pattern",
            )

        control_slots = _extract_car_control_slots(text)
        if control_slots:
            return self._frame(
                CommandType.CAR_CONTROL,
                slots=control_slots,
                confidence=0.88,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="car_control_slot_extracted",
            )

        if _contains_actionable_dangerous_control(text):
            return self._frame(
                CommandType.CAR_CONTROL,
                confidence=0.86,
                evidence=evidence,
                risk_signals=risk_signals,
                reason="actionable_dangerous_control",
            )

        results = self.retriever.search(user_input, top_k=1)
        if results and self._is_reliable_intent_match(user_input, results[0]):
            return self._frame(
                results[0].document.metadata["command_type"],
                confidence=min(0.82, 0.5 + results[0].score / 20),
                evidence=evidence,
                risk_signals=risk_signals,
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
                evidence=evidence,
                risk_signals=risk_signals,
                reason="local_llm_fallback",
            )
        return self._frame(
            CommandType.UNKNOWN,
            confidence=0.2,
            evidence=evidence,
            risk_signals=risk_signals,
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
            "NAVIGATION、CAR_CONTROL、CHARGE_PLAN、PERSONALIZE、UNKNOWN。"
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

    def _collect_evidence(self, content: str) -> Dict[str, object]:
        keyword_hits = []
        for document in INTENT_DOCUMENTS:
            for keyword in document.keywords:
                if keyword and keyword.lower() in (content or "").lower():
                    keyword_hits.append(keyword)
        for keyword in DANGEROUS_KEYWORDS:
            if keyword and keyword.lower() in (content or "").lower():
                keyword_hits.append(keyword)
        seen = set()
        keyword_hits = [
            keyword
            for keyword in keyword_hits
            if not (keyword.lower() in seen or seen.add(keyword.lower()))
        ]
        retrieval = [
            {
                "doc_id": item.document.doc_id,
                "score": item.score,
                "command_type": item.document.metadata.get("command_type"),
                "matched_keywords": item.matched_keywords,
            }
            for item in self.retriever.search(content, top_k=3)
        ]
        return {
            "keyword_hits": keyword_hits,
            "retrieval": retrieval,
        }

    def _collect_risk_signals(self, content: str) -> List[str]:
        signals = []
        for keyword in DANGEROUS_KEYWORDS:
            if keyword and keyword.lower() in (content or "").lower():
                signals.append(keyword)
        if _contains_actionable_dangerous_control(content):
            signals.append("actionable_dangerous_control")
        seen = set()
        return [
            signal
            for signal in signals
            if not (signal.lower() in seen or seen.add(signal.lower()))
        ]

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


def _is_non_actionable_question(content: str) -> bool:
    normalized = (content or "").replace(" ", "")
    question_markers = (
        "是什么",
        "什么意思",
        "介绍",
        "讲一下",
        "解释",
        "为什么",
        "如何",
        "怎么取消",
        "问问",
        "?",
        "？",
    )
    return any(marker in normalized for marker in question_markers)


def _is_negated_or_meta_request(content: str) -> bool:
    normalized = (content or "").replace(" ", "")
    negation_markers = ("不想", "不要", "不用", "别", "只是问", "问问怎么取消")
    return any(marker in normalized for marker in negation_markers)


def _is_charge_request(content: str) -> bool:
    return _contains_any(content, ["电量低", "补能", "充电", "换电", "续航不够"])


def _is_personalize_request(content: str) -> bool:
    return _contains_any(content, ["偏好", "用户画像", "个性化", "我的设置"])


def _extract_car_control_slots(content: str) -> Dict[str, object]:
    normalized = (content or "").replace(" ", "")
    slots: Dict[str, object] = {}

    temperature = re.search(r"(\d{1,2})\s*(?:度|℃)", content or "")
    if temperature and _contains_any(content, ["温度", "空调"]):
        slots["temperature_c"] = int(temperature.group(1))
        slots["target"] = "cabin_temperature"
        slots["action"] = "set"
        return slots

    if _contains_any(content, ["座椅加热"]):
        slots["target"] = "seat_heat"
        if _contains_any(content, ["打开", "开启", "启动"]):
            slots["action"] = "on"
            return slots
        if _contains_any(content, ["关闭", "关掉"]):
            slots["action"] = "off"
            return slots

    cabin_targets = ("空调", "车窗", "后备箱", "雨刷", "车灯", "座椅")
    action_words = ("打开", "开启", "关闭", "关掉", "调到", "调低", "调高")
    if any(target in normalized for target in cabin_targets) and any(
        action in normalized for action in action_words
    ):
        slots["target"] = "cabin_device"
        slots["action"] = "control"
        return slots

    return slots


def _contains_actionable_dangerous_control(content: str) -> bool:
    normalized = (content or "").replace(" ", "").lower()
    actionable_patterns = (
        "加速到",
        "立即加速",
        "提升动力",
        "动力提升",
        "立即刹车",
        "执行刹车",
        "紧急制动",
        "执行制动",
        "立即制动",
        "关闭aeb",
        "禁用aeb",
        "关闭自动紧急制动",
        "禁用自动紧急制动",
        "接管方向盘",
        "自动转向",
        "执行转向",
        "帮我转向",
    )
    return any(pattern in normalized for pattern in actionable_patterns)


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
