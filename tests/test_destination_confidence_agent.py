import pytest

from agents.cloud.destination_confidence_agent import DestinationConfidenceAgent
from providers.destination_models import DestinationCandidate
from providers.destination_resolver import DestinationClarificationRequired


class FakeCandidateProvider:
    provider_name = "fake_poi"

    def __init__(self, candidates):
        self.candidates = candidates
        self.queries = []

    def search_text(self, keyword, city="", limit=3):
        self.queries.append((keyword, city, limit))
        return self.candidates[:limit]


class FakeLLMClient:
    provider_name = "fake_llm"

    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate(self, system_prompt, user_prompt, context=None):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "context": context or {},
            }
        )
        return self.response


def _candidate(name, gps="121.50,31.25", confidence=0.91, address="上海市浦东新区"):
    return DestinationCandidate(
        name=name,
        gps=gps,
        address=address,
        source="fake_poi",
        confidence=confidence,
        reason="provider_text_search",
    )


def test_generic_destination_requires_candidate_confirmation_even_with_map_candidates():
    llm = FakeLLMClient(
        '{"decision":"AUTO_EXECUTE","confidence":0.99,'
        '"selected_candidate_index":0,"reason":"唯一候选"}'
    )
    agent = DestinationConfidenceAgent(llm_client=llm)

    with pytest.raises(DestinationClarificationRequired) as context:
        agent.ensure_executable(
            "导航去世博园",
            candidate_provider=FakeCandidateProvider(
                [
                    _candidate("上海世博园", address="上海市浦东新区世博大道"),
                    _candidate("昆明世博园", gps="102.75,25.07", address="云南省昆明市"),
                ]
            ),
        )

    assert context.value.reason == "destination_candidate_confirmation"
    assert context.value.query == "世博园"
    assert [item["name"] for item in context.value.candidates] == [
        "上海世博园",
        "昆明世博园",
    ]
    assert llm.calls


def test_frequent_destination_can_be_executed_without_confirmation():
    llm = FakeLLMClient('{"decision":"NEEDS_CLARIFICATION","confidence":0.2}')
    agent = DestinationConfidenceAgent(llm_client=llm)

    decision = agent.ensure_executable(
        "导航去世博园",
        candidate_provider=FakeCandidateProvider([_candidate("上海世博园")]),
        frequent_destinations={"世博园"},
    )

    assert decision.decision == "AUTO_EXECUTE"
    assert decision.reason == "frequent_user_destination"
    assert llm.calls == []


def test_configured_common_local_landmark_can_execute_without_llm_confirmation():
    llm = FakeLLMClient('{"decision":"NEEDS_CLARIFICATION","confidence":0.2}')
    agent = DestinationConfidenceAgent(llm_client=llm)

    decision = agent.ensure_executable(
        "导航去外滩",
        candidate_provider=FakeCandidateProvider([_candidate("上海外滩")]),
    )

    assert decision.decision == "AUTO_EXECUTE"
    assert decision.reason == "common_local_destination"
    assert llm.calls == []


def test_specific_destination_without_provider_can_continue_to_execution_layer():
    llm = FakeLLMClient('{"decision":"NEEDS_CLARIFICATION","confidence":0.2}')
    agent = DestinationConfidenceAgent(llm_client=llm)

    decision = agent.ensure_executable("导航去北京东方广场蔚来中心")

    assert decision.decision == "AUTO_EXECUTE"
    assert decision.reason == "specific_destination_without_preflight_provider"
    assert llm.calls == []


def test_specific_destination_still_needs_clarification_when_llm_confidence_is_not_high():
    llm = FakeLLMClient(
        '{"decision":"NEEDS_CLARIFICATION","confidence":0.67,'
        '"selected_candidate_index":0,"reason":"用户输入缺少门店唯一信息"}'
    )
    agent = DestinationConfidenceAgent(llm_client=llm)

    with pytest.raises(DestinationClarificationRequired) as context:
        agent.ensure_executable(
            "导航去北京蔚来中心",
            candidate_provider=FakeCandidateProvider(
                [
                    _candidate(
                        "北京东方广场蔚来中心",
                        gps="116.417,39.915",
                        address="北京市东城区东方广场",
                    ),
                    _candidate(
                        "北京朝阳合生汇蔚来中心",
                        gps="116.475,39.909",
                        address="北京市朝阳区合生汇",
                    ),
                ]
            ),
        )

    assert context.value.reason == "destination_candidate_confirmation"
    assert len(context.value.candidates) == 2
    assert "缺少门店唯一信息" in context.value.suggestions[0]
    assert llm.calls
