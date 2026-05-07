from agents.vehicle.intent.evidence import IntentEvidenceCollector
from agents.vehicle.intent.rule_engine import IntentRuleEngine
from agents.vehicle.intent.slot_extractor import SlotExtractor
from core.constants import CommandType
from rag.documents import INTENT_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


def test_slot_extractor_keeps_full_destination_query():
    slots = SlotExtractor().extract("导航去北京的蔚来中心")

    assert slots["navigation"]["raw_destination"] == "北京的蔚来中心"
    assert slots["navigation"]["destination_query"] == "北京蔚来中心"


def test_slot_extractor_extracts_info_query_topic():
    slots = SlotExtractor().extract("讲一下制动距离")

    assert slots["info_query"]["topic"] == "制动距离"


def test_rule_engine_prefers_info_query_over_unknown_question():
    retriever = SimpleRetriever(INTENT_DOCUMENTS)
    frame = IntentRuleEngine(retriever=retriever).analyze("AEB是什么")

    assert frame.command_type == CommandType.INFO_QUERY
    assert frame.reason == "info_query_pattern"


def test_rule_engine_keeps_dangerous_action_as_car_control():
    retriever = SimpleRetriever(INTENT_DOCUMENTS)
    frame = IntentRuleEngine(retriever=retriever).analyze("关闭AEB")

    assert frame.command_type == CommandType.CAR_CONTROL
    assert "actionable_dangerous_control" in frame.risk_signals


def test_evidence_collector_deduplicates_keywords():
    retriever = SimpleRetriever(INTENT_DOCUMENTS)
    evidence = IntentEvidenceCollector(retriever=retriever).collect("AEB是什么")

    assert evidence["keyword_hits"].count("AEB") == 1
    assert isinstance(evidence["retrieval"], list)
