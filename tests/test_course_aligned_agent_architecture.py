import unittest
import uuid
from pathlib import Path

from agents.cloud.vector_knowledge_agent import VectorKnowledgeAgent
from agents.orchestrator.global_dispatch_agent import GlobalDispatchAgent
from agents.vehicle.cabin_vehicle_control_agent import CabinVehicleControlAgent
from agents.vehicle.data_upload_agent import DataUploadAgent
from agents.vehicle.global_safety_dispatch_agent import GlobalSafetyDispatchAgent
from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.message import Message
from core.vehicle_core_service import ExecutionResult, VehicleCoreService
from memory.local_agent_context_manager import LocalAgentContextManager


def make_result(
    user_input,
    command_type=CommandType.NAVIGATION,
    status=ExecutionStatus.EXECUTED,
    network=NetworkStatus.ONLINE,
    output="ok",
    user_id="user_001",
):
    message = Message.create(
        user_id=user_id,
        command_type=command_type,
        safety=SafetyLevel.SAFE,
        content=user_input,
        network=network,
    )
    return ExecutionResult(status=status, output=output, message=message)


class TestCourseAlignedAgentArchitecture(unittest.TestCase):
    def test_global_dispatch_agent_exposes_course_aligned_tools(self):
        agent = GlobalDispatchAgent()

        self.assertEqual(agent.role_name, "全局调度 Agent")
        self.assertEqual(agent.business_agent_count, 8)
        self.assertIn("knowledge.retrieve", agent.tool_registry.list_names())
        self.assertIn("trip.plan", agent.tool_registry.list_names())

    def test_vector_knowledge_agent_retrieves_route_and_profile_context(self):
        agent = VectorKnowledgeAgent()

        results = agent.retrieve("电量低", user_id="user_002", command_type=CommandType.CHARGE_PLAN)
        texts = [item.document.text for item in results]

        self.assertTrue(any("电量低于20%" in text for text in texts))
        self.assertTrue(any("user_002" in text for text in texts))

    def test_vector_knowledge_agent_does_not_mix_intent_examples_into_cloud_rag(self):
        agent = VectorKnowledgeAgent()

        results = agent.retrieve(
            "导航去121.486754,31.186881",
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
        )

        self.assertTrue(results)
        self.assertFalse(any(item.document.doc_id.startswith("intent_") for item in results))

    def test_vector_knowledge_agent_filters_weak_navigation_keyword_matches(self):
        agent = VectorKnowledgeAgent()

        results = agent.retrieve(
            "导航去蔚来中心",
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
        )

        doc_ids = [item.document.doc_id for item in results]
        self.assertIn("profile_user_001", doc_ids)
        self.assertNotIn("route_highway_preference", doc_ids)
        self.assertNotIn("route_offline_navigation", doc_ids)

        long_trip_results = agent.retrieve(
            "长途走高速去蔚来中心",
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
        )
        long_trip_doc_ids = [item.document.doc_id for item in long_trip_results]
        self.assertIn("route_highway_preference", long_trip_doc_ids)

    def test_local_context_is_scoped_by_agent_id(self):
        path = Path(".test_runtime") / f"agent_context_{uuid.uuid4().hex}.json"
        manager = LocalAgentContextManager(path=path, max_recent_turns=3)

        manager.record_result(make_result("打开座椅加热"), agent_id="local_intent")
        manager.record_result(make_result("生成行程摘要"), agent_id="local_summary")

        intent_snapshot = manager.snapshot("user_001", agent_id="local_intent")
        summary_snapshot = manager.snapshot("user_001", agent_id="local_summary")

        self.assertEqual(intent_snapshot["agent_id"], "local_intent")
        self.assertEqual(summary_snapshot["agent_id"], "local_summary")
        self.assertEqual(intent_snapshot["total_turns"], 1)
        self.assertEqual(summary_snapshot["total_turns"], 1)
        self.assertEqual(intent_snapshot["recent_turns"][0]["user_input"], "打开座椅加热")

    def test_vehicle_service_uses_course_aligned_agent_trace(self):
        path = Path(".test_runtime") / f"agent_context_{uuid.uuid4().hex}.json"
        context_manager = LocalAgentContextManager(path=path)
        service = VehicleCoreService(context_manager=context_manager)

        result = service.run("导航去蔚来中心", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.EXECUTED)
        self.assertTrue(any(item["tool_name"] == "knowledge.retrieve" for item in result.trace))
        self.assertTrue(any(item["tool_name"] == "trip.plan" for item in result.trace))

    def test_edge_business_agents_have_explicit_roles(self):
        self.assertEqual(GlobalSafetyDispatchAgent().role_name, "全局安全调度 Agent")
        self.assertEqual(CabinVehicleControlAgent().role_name, "座舱/车控 Agent")
        self.assertEqual(DataUploadAgent().role_name, "数据上报 Agent")


if __name__ == "__main__":
    unittest.main()
