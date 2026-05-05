from agents.vehicle.local_intent_agent import LocalIntentAgent
from core.constants import ExecutionStatus, SafetyLevel
from core.vehicle_core_service import VehicleCoreService
from data.offline_scenarios import OFFLINE_SCENARIOS


class OfflineEvaluator:
    def __init__(self, scenarios=None, service=None):
        self.scenarios = scenarios or OFFLINE_SCENARIOS
        self.service = service or VehicleCoreService()
        self.intent_agent = LocalIntentAgent()

    def run(self) -> dict:
        failed_cases = []
        intent_correct = 0
        safety_correct = 0
        status_correct = 0
        rag_hits = 0
        rag_expected = 0
        dangerous_total = 0
        dangerous_blocked = 0

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

            if scenario.expected_safety == SafetyLevel.DANGEROUS:
                dangerous_total += 1
                dangerous_blocked += int(result.status == ExecutionStatus.BLOCKED)

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
            "safety_block_recall": _rate(dangerous_blocked, dangerous_total),
            "rag_hit_rate": _rate(rag_hits, rag_expected),
            "failed_cases": failed_cases,
        }


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)
