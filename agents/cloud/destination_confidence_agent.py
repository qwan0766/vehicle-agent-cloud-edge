from dataclasses import dataclass
import json

from llm.factory import create_llm_client
from providers.destination_models import DestinationCandidate
from providers.destination_query import (
    extract_destination_query,
    looks_like_gps,
    normalize_destination_query,
)
from providers.destination_resolver import DestinationClarificationRequired
from providers.destination_service import KNOWN_DESTINATIONS


@dataclass(frozen=True)
class DestinationConfidenceDecision:
    decision: str
    confidence: float
    reason: str
    selected_candidate: dict = None


class DestinationConfidenceAgent:
    role_name = "目的地置信度 Agent"

    def __init__(self, llm_client=None, auto_execute_threshold: float = 0.92):
        self.llm_client = llm_client or create_llm_client()
        self.auto_execute_threshold = auto_execute_threshold
        self._last_trace = []

    def ensure_executable(
        self,
        content: str,
        candidate_provider=None,
        geocoder=None,
        frequent_destinations=None,
    ) -> DestinationConfidenceDecision:
        self._last_trace = []
        query = normalize_destination_query(extract_destination_query(content) or content)
        frequent_destinations = {
            normalize_destination_query(item) for item in (frequent_destinations or set())
        }

        if not query or looks_like_gps(query):
            return DestinationConfidenceDecision("AUTO_EXECUTE", 1.0, "explicit_or_empty")
        if query in frequent_destinations:
            return DestinationConfidenceDecision("AUTO_EXECUTE", 1.0, "frequent_user_destination")
        if query in KNOWN_DESTINATIONS:
            return DestinationConfidenceDecision("AUTO_EXECUTE", 1.0, "known_destination")
        if query in _COMMON_LOCAL_DESTINATIONS:
            return DestinationConfidenceDecision("AUTO_EXECUTE", 0.96, "common_local_destination")

        candidates = self._collect_candidates(query, candidate_provider, geocoder)
        if not candidates and _has_strong_specificity(query):
            return DestinationConfidenceDecision(
                "AUTO_EXECUTE",
                0.9,
                "specific_destination_without_preflight_provider",
            )
        if _is_generic_destination(query):
            llm_reason = ""
            if candidates:
                llm_reason = self._llm_assess(query, candidates).reason
            raise self._clarification(
                query,
                candidates,
                llm_reason or "泛化地点需要用户确认唯一目的地。",
            )

        llm_decision = self._llm_assess(query, candidates)
        if (
            llm_decision.decision == "AUTO_EXECUTE"
            and llm_decision.confidence >= self.auto_execute_threshold
            and _has_strong_specificity(query)
        ):
            return llm_decision

        reason = llm_decision.reason or "目的地置信度不足，需要用户确认。"
        raise self._clarification(query, candidates, reason)

    def get_last_trace(self):
        return [dict(item) for item in self._last_trace]

    def _collect_candidates(self, query: str, candidate_provider, geocoder):
        candidates = []
        if candidate_provider and hasattr(candidate_provider, "search_text"):
            candidates = candidate_provider.search_text(query, limit=3)
        elif geocoder:
            result = geocoder.geocode(query)
            candidates = [
                DestinationCandidate(
                    name=result.name or query,
                    gps=result.gps,
                    address=getattr(result, "formatted_address", ""),
                    source=getattr(geocoder, "provider_name", "geocoder"),
                    confidence=getattr(result, "confidence", 0.0),
                    reason=getattr(result, "quality_reason", "geocode_candidate"),
                )
            ]
        payload = [_candidate_payload(item) for item in candidates]
        self._last_trace.append(
            {
                "tool_name": "destination.candidates",
                "input": {"query": query},
                "output": {"count": len(payload), "candidates": payload},
                "duration_ms": 0,
            }
        )
        return payload

    def _llm_assess(self, query: str, candidates: list) -> DestinationConfidenceDecision:
        response = self.llm_client.generate(
            system_prompt=(
                "你是车载导航目的地置信度 Agent。你不能编造地点或坐标，只能基于"
                "地图候选判断是否可以直接导航。除非用户输入足够具体且候选唯一，"
                "否则输出 NEEDS_CLARIFICATION。只输出 JSON。"
            ),
            user_prompt=f"用户目的地：{query}",
            context={
                "query": query,
                "candidates": candidates,
                "allowed_decisions": ["AUTO_EXECUTE", "NEEDS_CLARIFICATION"],
                "auto_execute_threshold": self.auto_execute_threshold,
            },
        )
        self._last_trace.append(
            {
                "tool_name": "destination.llm_confidence",
                "input": {"query": query, "candidate_count": len(candidates)},
                "output": response,
                "duration_ms": 0,
            }
        )
        payload = _parse_json_object(response)
        decision = str(payload.get("decision", "NEEDS_CLARIFICATION")).upper()
        if decision not in {"AUTO_EXECUTE", "NEEDS_CLARIFICATION"}:
            decision = "NEEDS_CLARIFICATION"
        confidence = _safe_float(payload.get("confidence"), 0.0)
        index = payload.get("selected_candidate_index")
        selected = _select_candidate(candidates, index)
        return DestinationConfidenceDecision(
            decision=decision,
            confidence=confidence,
            reason=str(payload.get("reason", "")),
            selected_candidate=selected,
        )

    def _clarification(self, query: str, candidates: list, reason: str):
        if not candidates:
            return DestinationClarificationRequired(
                query,
                "no_destination_candidates",
                suggestions=(
                    f"候选列表为空：地图没有找到与“{query}”匹配的可导航 POI。",
                    "请补充城市、商圈、门店名或完整地址；如果是主观描述，请改成具体地点名称。",
                ),
                candidates=[],
            )
        return DestinationClarificationRequired(
            query,
            "destination_candidate_confirmation",
            suggestions=(
                reason,
                "请选择一个候选地点，或补充城市、商圈、门店名、完整地址后再导航。",
            ),
            candidates=candidates,
        )


def _candidate_payload(candidate):
    if isinstance(candidate, dict):
        return dict(candidate)
    if hasattr(candidate, "to_payload"):
        return candidate.to_payload()
    return {
        "name": getattr(candidate, "name", ""),
        "gps": getattr(candidate, "gps", ""),
        "address": getattr(candidate, "address", ""),
        "source": getattr(candidate, "source", ""),
        "confidence": getattr(candidate, "confidence", 0.0),
        "distance_km": getattr(candidate, "distance_km", None),
        "reason": getattr(candidate, "reason", ""),
    }


def _parse_json_object(text: str) -> dict:
    raw = (text or "").strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _select_candidate(candidates: list, index):
    try:
        candidate_index = int(index)
    except (TypeError, ValueError):
        return None
    if candidate_index >= 1:
        candidate_index -= 1
    if 0 <= candidate_index < len(candidates):
        return candidates[candidate_index]
    return None


def _is_generic_destination(query: str) -> bool:
    if _has_strong_specificity(query):
        return False
    if any(region in query for region in _REGION_HINTS):
        return False
    if query in {"机场", "火车站", "高铁站", "车站", "医院", "学校", "公园", "商场"}:
        return True
    if any(query.endswith(marker) for marker in ("园", "中心", "广场", "公园", "机场", "车站")):
        return True
    return False


def _has_strong_specificity(query: str) -> bool:
    has_region = any(region in query for region in _REGION_HINTS)
    has_venue = any(venue in query for venue in _VENUE_HINTS)
    has_address_marker = any(marker in query for marker in ("路", "街", "号", "大厦", "商场"))
    return has_region and (has_venue or has_address_marker)


_REGION_HINTS = (
    "北京",
    "上海",
    "杭州",
    "广州",
    "深圳",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "浦东",
    "黄浦",
    "朝阳",
    "东城",
    "西湖",
    "萧山",
)

_VENUE_HINTS = (
    "东方广场",
    "印象城",
    "合生汇",
    "国贸",
    "万象城",
    "环球港",
    "陆家嘴",
    "外滩",
    "虹桥",
    "萧山",
)

_COMMON_LOCAL_DESTINATIONS = {
    "外滩",
    "陆家嘴",
    "静安寺",
    "东方明珠",
    "人民广场",
    "西湖",
}
