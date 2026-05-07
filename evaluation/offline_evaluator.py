from agents.vehicle.local_intent_agent import LocalIntentAgent
from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from agents.cloud.cloud_ecology_agent import CloudEcologyAgent
from agents.cloud.cloud_schedule_agent import CloudScheduleAgent
from core.constants import ExecutionStatus, SafetyLevel
from core.vehicle_core_service import VehicleCoreService
from data.offline_scenarios import OFFLINE_SCENARIOS
from llm.mock_llm_client import MockLLMClient
from providers.offline_charge_provider import OfflineChargeProvider
from providers.offline_map_provider import OfflineMapProvider
from providers.offline_weather_provider import OfflineWeatherProvider


class OfflineEvaluator:
    def __init__(self, scenarios=None, service=None):
        self.scenarios = scenarios or OFFLINE_SCENARIOS
        mock_llm = MockLLMClient()
        offline_route_agent = CloudRoutePlanAgent(
            llm_client=mock_llm,
            map_provider=OfflineMapProvider(),
        )
        offline_ecology_agent = CloudEcologyAgent(
            weather_provider=OfflineWeatherProvider(),
            charge_provider=OfflineChargeProvider(),
        )
        self.service = service or VehicleCoreService(
            cloud_agent=CloudScheduleAgent(
                ecology_agent=offline_ecology_agent,
                route_agent=offline_route_agent,
                llm_client=mock_llm,
            )
        )
        self.intent_agent = LocalIntentAgent()

    def run(self) -> dict:
        failed_cases = []
        intent_correct = 0
        safety_correct = 0
        status_correct = 0
        rag_hits = 0
        rag_expected = 0
        hard_danger_total = 0
        hard_danger_blocked = 0
        driver_confirmation_total = 0
        driver_confirmation_matched = 0

        for scenario in self.scenarios:
            result = self.service.run(
                scenario.content,
                user_id=scenario.user_id,
                network=scenario.network,
            )
            actual = result.message

            checks = {
                "intent": actual.command_type == scenario.expected_intent,
                "safety": actual.safety == scenario.expected_safety,
                "status": result.status == scenario.expected_status,
            }

            intent_correct += int(checks["intent"])
            safety_correct += int(checks["safety"])
            status_correct += int(checks["status"])

            if scenario.expected_rag_hit:
                rag_expected += 1
                rag_hits += int(bool(self.intent_agent.retrieve_context(scenario.content)))

            if (
                scenario.expected_safety == SafetyLevel.DANGEROUS
                and scenario.expected_status == ExecutionStatus.BLOCKED
            ):
                hard_danger_total += 1
                hard_danger_blocked += int(result.status == ExecutionStatus.BLOCKED)

            if scenario.expected_status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION:
                driver_confirmation_total += 1
                driver_confirmation_matched += int(
                    result.status == ExecutionStatus.NEEDS_DRIVER_CONFIRMATION
                )

            if not all(checks.values()):
                failed_cases.append(
                    {
                        "case_id": scenario.case_id,
                        "content": scenario.content,
                        "checks": checks,
                        "actual_intent": actual.command_type.value,
                        "actual_safety": actual.safety.value,
                        "actual_status": result.status.value,
                    }
                )

        total = len(self.scenarios)
        return {
            "total": total,
            "intent_accuracy": _rate(intent_correct, total),
            "safety_accuracy": _rate(safety_correct, total),
            "status_accuracy": _rate(status_correct, total),
            "safety_block_recall": _rate(hard_danger_blocked, hard_danger_total),
            "driver_confirmation_recall": _rate(
                driver_confirmation_matched,
                driver_confirmation_total,
            ),
            "rag_hit_rate": _rate(rag_hits, rag_expected),
            "failed_cases": failed_cases,
        }


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)
