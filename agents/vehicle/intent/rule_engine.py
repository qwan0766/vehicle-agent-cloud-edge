from core.constants import CommandType
from data.knowledge_base import INTENT_KNOWLEDGE
from agents.vehicle.intent.evidence import (
    IntentEvidenceCollector,
    contains_actionable_dangerous_control,
    contains_any,
)
from agents.vehicle.intent.models import IntentFrame
from agents.vehicle.intent.slot_extractor import SlotExtractor


class IntentRuleEngine:
    def __init__(self, retriever, slot_extractor=None, evidence_collector=None):
        self.retriever = retriever
        self.slot_extractor = slot_extractor or SlotExtractor()
        self.evidence_collector = evidence_collector or IntentEvidenceCollector(retriever)

    def analyze(self, user_input: str) -> IntentFrame:
        text = (user_input or "").strip()
        evidence = self.evidence_collector.collect(text)
        risk_signals = self.evidence_collector.risk_signals(text)
        slots = self.slot_extractor.extract(text)

        if not text:
            return _frame(CommandType.UNKNOWN, 0.0, evidence, risk_signals, "empty_input")

        for example, command_type in INTENT_KNOWLEDGE.items():
            if text == example:
                return _frame(
                    command_type,
                    0.98,
                    evidence,
                    risk_signals,
                    "exact_builtin_example",
                )

        if is_negated_or_meta_request(text):
            return _frame(
                CommandType.UNKNOWN,
                0.25,
                evidence,
                risk_signals,
                "negated_or_meta_request",
            )

        if is_non_actionable_question(text) and not is_charge_request(text):
            if slots["info_query"]:
                return _frame(
                    CommandType.INFO_QUERY,
                    0.82,
                    evidence,
                    risk_signals,
                    "info_query_pattern",
                    slots["info_query"],
                )
            return _frame(
                CommandType.UNKNOWN,
                0.35,
                evidence,
                risk_signals,
                "non_actionable_question",
            )

        if slots["navigation"]:
            return _frame(
                CommandType.NAVIGATION,
                0.94,
                evidence,
                risk_signals,
                "navigation_slot_extracted",
                slots["navigation"],
            )

        if is_charge_request(text):
            return _frame(
                CommandType.CHARGE_PLAN,
                0.9,
                evidence,
                risk_signals,
                "charge_request_pattern",
            )

        if is_personalize_request(text):
            return _frame(
                CommandType.PERSONALIZE,
                0.9,
                evidence,
                risk_signals,
                "personalize_request_pattern",
            )

        if slots["car_control"]:
            return _frame(
                CommandType.CAR_CONTROL,
                0.88,
                evidence,
                risk_signals,
                "car_control_slot_extracted",
                slots["car_control"],
            )

        if contains_actionable_dangerous_control(text):
            return _frame(
                CommandType.CAR_CONTROL,
                0.86,
                evidence,
                risk_signals,
                "actionable_dangerous_control",
            )

        return _frame(
            CommandType.UNKNOWN,
            0.2,
            evidence,
            risk_signals,
            "no_rule_match",
        )


def _frame(command_type, confidence, evidence, risk_signals, reason, slots=None):
    return IntentFrame(
        command_type=command_type,
        slots=slots or {},
        confidence=confidence,
        evidence=evidence or {"keyword_hits": [], "retrieval": []},
        risk_signals=risk_signals or [],
        reason=reason,
    )


def is_non_actionable_question(content: str) -> bool:
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


def is_negated_or_meta_request(content: str) -> bool:
    normalized = (content or "").replace(" ", "")
    negation_markers = ("不想", "不要", "不用", "别", "只是问", "问问怎么取消")
    return any(marker in normalized for marker in negation_markers)


def is_charge_request(content: str) -> bool:
    return contains_any(content, ["电量低", "补能", "充电", "换电", "续航不够"])


def is_personalize_request(content: str) -> bool:
    return contains_any(content, ["偏好", "用户画像", "个性化", "我的设置"])
