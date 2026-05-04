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


if __name__ == "__main__":
    unittest.main()
