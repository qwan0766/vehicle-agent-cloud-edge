import unittest

from core.constants import CommandType, NetworkStatus, SafetyLevel
from core.message import Message


class TestCoreMessage(unittest.TestCase):
    def test_message_carries_unified_request_fields(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去蔚来中心",
            network=NetworkStatus.ONLINE,
        )

        self.assertTrue(msg.request_id)
        self.assertEqual(msg.user_id, "user_001")
        self.assertEqual(msg.command_type, CommandType.NAVIGATION)
        self.assertEqual(msg.safety, SafetyLevel.SAFE)
        self.assertEqual(msg.content, "导航去蔚来中心")
        self.assertEqual(msg.network, NetworkStatus.ONLINE)


if __name__ == "__main__":
    unittest.main()
