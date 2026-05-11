import uuid
import unittest
from pathlib import Path

from feedback.preference_store import PreferenceStore
from feedback.preference_updater import PreferenceUpdate


class TestPreferenceStore(unittest.TestCase):
    def test_applies_preference_update_to_user_state(self):
        path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        store = PreferenceStore(path)
        update = PreferenceUpdate(
            user_id="user_002",
            preference_key="route_preference_highway",
            delta=1,
            description="路线偏好高速 +1",
            timestamp="2026-05-05T00:00:00",
        )

        state = store.apply(update)

        self.assertEqual(state["route_preference_highway"], 1)
        self.assertEqual(store.get_user_state("user_002")["route_preference_highway"], 1)

    def test_applies_structured_long_term_memory_without_breaking_legacy_counter(self):
        path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        store = PreferenceStore(path)
        update = PreferenceUpdate(
            user_id="user_001",
            preference_key="route_preference_highway",
            delta=1,
            description="路线偏好高速 +1",
            timestamp="2026-05-05T00:00:00",
            memory_key="route_preference",
            memory_value="高速优先",
            source="repeated_behavior",
            confidence_delta=0.12,
        )

        state = store.apply(update)

        self.assertEqual(state["route_preference_highway"], 1)
        memory = state["long_term_memory"]["route_preference"]
        self.assertEqual(memory["value"], "高速优先")
        self.assertEqual(memory["source"], "repeated_behavior")
        self.assertEqual(memory["evidence_count"], 1)
        self.assertEqual(memory["updated_at"], "2026-05-05T00:00:00")
        self.assertGreaterEqual(memory["confidence"], 0.5)
        self.assertLessEqual(memory["confidence"], 0.95)

    def test_repeated_structured_updates_raise_confidence_and_evidence_count(self):
        path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        store = PreferenceStore(path)

        for index in range(3):
            store.apply(
                PreferenceUpdate(
                    user_id="user_001",
                    preference_key="route_preference_highway",
                    delta=1,
                    description="路线偏好高速 +1",
                    timestamp=f"2026-05-05T00:00:0{index}",
                    memory_key="route_preference",
                    memory_value="高速优先",
                    source="repeated_behavior",
                    confidence_delta=0.12,
                )
            )

        state = store.get_user_state("user_001")
        memory = state["long_term_memory"]["route_preference"]
        self.assertEqual(state["route_preference_highway"], 3)
        self.assertEqual(memory["evidence_count"], 3)
        self.assertGreaterEqual(memory["confidence"], 0.74)

    def test_zero_delta_update_does_not_create_long_term_memory(self):
        path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        store = PreferenceStore(path)
        update = PreferenceUpdate(
            user_id="user_001",
            preference_key="clarification_pending",
            delta=0,
            description="等待用户澄清，不更新偏好",
            timestamp="2026-05-05T00:00:00",
            memory_key="route_preference",
            memory_value="高速优先",
            source="guardrail",
            confidence_delta=0.12,
        )

        state = store.apply(update)

        self.assertEqual(state["clarification_pending"], 0)
        self.assertNotIn("long_term_memory", state)

    def test_explicit_preference_has_more_confidence_than_single_behavior_signal(self):
        behavior_path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        explicit_path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        behavior_store = PreferenceStore(behavior_path)
        explicit_store = PreferenceStore(explicit_path)

        behavior_state = behavior_store.apply(
            PreferenceUpdate(
                user_id="user_001",
                preference_key="route_preference_highway",
                delta=1,
                description="behavior evidence",
                timestamp="2026-05-05T00:00:00",
                memory_key="route_preference",
                memory_value="highway_first",
                source="repeated_behavior",
                evidence_type="behavior",
                confidence_weight=0.08,
            )
        )
        explicit_state = explicit_store.apply(
            PreferenceUpdate(
                user_id="user_001",
                preference_key="route_preference_highway",
                delta=1,
                description="user explicitly confirmed highway preference",
                timestamp="2026-05-05T00:00:00",
                memory_key="route_preference",
                memory_value="highway_first",
                source="user_confirmation",
                evidence_type="explicit_preference",
                confidence_weight=0.25,
            )
        )

        behavior_confidence = behavior_state["long_term_memory"]["route_preference"]["confidence"]
        explicit_confidence = explicit_state["long_term_memory"]["route_preference"]["confidence"]
        self.assertGreater(explicit_confidence, behavior_confidence)

    def test_negative_evidence_reduces_confidence_without_erasing_memory(self):
        path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        store = PreferenceStore(path)
        store.apply(
            PreferenceUpdate(
                user_id="user_001",
                preference_key="route_preference_highway",
                delta=1,
                description="positive route evidence",
                timestamp="2026-05-05T00:00:00",
                memory_key="route_preference",
                memory_value="highway_first",
                source="repeated_behavior",
                evidence_type="behavior",
                confidence_weight=0.18,
            )
        )
        before = store.get_long_term_memory("user_001")["route_preference"]["confidence"]

        state = store.apply(
            PreferenceUpdate(
                user_id="user_001",
                preference_key="route_preference_highway",
                delta=-1,
                description="user asked not to use highway this time",
                timestamp="2026-05-05T00:05:00",
                memory_key="route_preference",
                memory_value="highway_first",
                source="negative_feedback",
                evidence_type="explicit_preference",
                polarity="negative",
                confidence_weight=0.16,
            )
        )

        memory = state["long_term_memory"]["route_preference"]
        self.assertLess(memory["confidence"], before)
        self.assertEqual(memory["positive_evidence_count"], 1)
        self.assertEqual(memory["negative_evidence_count"], 1)
        self.assertEqual(memory["last_negative_at"], "2026-05-05T00:05:00")

    def test_structured_memory_records_evidence_metadata(self):
        path = Path(".test_runtime") / f"preference_state_{uuid.uuid4().hex}.json"
        store = PreferenceStore(path)

        state = store.apply(
            PreferenceUpdate(
                user_id="user_001",
                preference_key="route_preference_highway",
                delta=1,
                description="long trip route evidence",
                timestamp="2026-05-05T00:00:00",
                memory_key="route_preference",
                memory_value="highway_first",
                source="repeated_behavior",
                evidence_type="behavior",
                scenario="long_trip",
                confidence_weight=0.08,
            )
        )

        memory = state["long_term_memory"]["route_preference"]
        self.assertEqual(memory["evidence_type"], "behavior")
        self.assertEqual(memory["scenario"], "long_trip")
        self.assertEqual(memory["positive_evidence_count"], 1)
        self.assertEqual(memory["negative_evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()
