import unittest

from agents.cloud.document_rag_agent import DocumentRAGAgent
from agents.cloud.rule_knowledge_agent import RuleKnowledgeAgent
from agents.cloud.vector_knowledge_agent import VectorKnowledgeAgent
from core.constants import CommandType
from rag.documents import ROUTE_DOCUMENTS
from rag.simple_retriever import SimpleRetriever


class TestSimpleRetriever(unittest.TestCase):
    def test_retrieves_route_document_by_keyword_overlap(self):
        retriever = SimpleRetriever(ROUTE_DOCUMENTS)

        results = retriever.search("电量低，需要补能", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertIn("换电站", results[0].document.text)
        self.assertGreater(results[0].score, 0)

    def test_returns_empty_list_when_nothing_matches(self):
        retriever = SimpleRetriever(ROUTE_DOCUMENTS)

        results = retriever.search("播放爵士音乐", top_k=2)

        self.assertEqual(results, [])

    def test_navigation_does_not_retrieve_long_trip_policy_from_generic_destination(self):
        results = VectorKnowledgeAgent().retrieve(
            "导航去蔚来中心",
            command_type=CommandType.NAVIGATION,
            top_k=3,
        )

        doc_ids = {item.document.doc_id for item in results}

        self.assertNotIn("route_highway_preference", doc_ids)

    def test_navigation_retrieves_long_trip_policy_when_long_trip_is_explicit(self):
        results = VectorKnowledgeAgent().retrieve(
            "长途走高速去蔚来中心",
            command_type=CommandType.NAVIGATION,
            top_k=3,
        )

        doc_ids = {item.document.doc_id for item in results}

        self.assertIn("route_highway_preference", doc_ids)

    def test_rule_knowledge_agent_returns_structured_policy_not_document_rag(self):
        results = RuleKnowledgeAgent().retrieve("电量低，需要补能", CommandType.CHARGE_PLAN)

        self.assertTrue(results)
        self.assertTrue(all(item.document.metadata.get("knowledge_type") == "structured_rule" for item in results))
        self.assertIn("route_low_battery_swap", {item.document.doc_id for item in results})

    def test_document_rag_agent_is_for_unstructured_manual_questions(self):
        results = DocumentRAGAgent().retrieve("AEB是什么", top_k=2)

        self.assertTrue(results)
        self.assertTrue(all(item.document.metadata.get("knowledge_type") == "document_rag" for item in results))
        self.assertIn("vehicle_manual_aeb", {item.document.doc_id for item in results})

    def test_document_rag_agent_loads_markdown_corpus_files(self):
        agent = DocumentRAGAgent()

        doc_ids = {document.doc_id for document in agent.documents}
        source_paths = {document.metadata.get("source_path") for document in agent.documents}

        self.assertIn("vehicle_manual_aeb", doc_ids)
        self.assertIn("energy_policy_low_battery", doc_ids)
        self.assertIn("navigation_offline_fallback", doc_ids)
        self.assertTrue(all(str(path).endswith(".md") for path in source_paths))

    def test_document_rag_agent_retrieves_common_vehicle_manual_topics(self):
        agent = DocumentRAGAgent()

        queries = {
            "AEB是什么": "vehicle_manual_aeb",
            "严重低电量还能开座椅加热吗": "energy_policy_low_battery",
            "断网以后导航怎么办": "navigation_offline_fallback",
            "雨天辅助驾驶要注意什么": "assisted_driving_weather",
        }

        for query, expected_doc_id in queries.items():
            with self.subTest(query=query):
                results = agent.retrieve(query, top_k=3)
                self.assertIn(expected_doc_id, {item.document.doc_id for item in results})

    def test_vector_knowledge_agent_does_not_mix_user_profile_into_knowledge_retrieval(self):
        results = VectorKnowledgeAgent().retrieve(
            "导航去蔚来中心",
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            top_k=5,
        )

        self.assertFalse(any(item.document.doc_id.startswith("profile_") for item in results))

    def test_vector_knowledge_agent_disables_document_rag_for_plain_navigation(self):
        agent = VectorKnowledgeAgent()

        results = agent.retrieve("导航去蔚来中心", command_type=CommandType.NAVIGATION)

        self.assertFalse(
            any(item.document.metadata.get("knowledge_type") == "document_rag" for item in results)
        )
        self.assertFalse(agent.last_policy["document_rag_enabled"])
        self.assertEqual(agent.last_policy["document_rag_reason"], "not_required")

    def test_vector_knowledge_agent_enables_document_rag_for_info_query(self):
        agent = VectorKnowledgeAgent()

        results = agent.retrieve("AEB是什么", command_type=CommandType.INFO_QUERY)

        self.assertTrue(
            any(item.document.metadata.get("knowledge_type") == "document_rag" for item in results)
        )
        self.assertTrue(agent.last_policy["document_rag_enabled"])
        self.assertEqual(agent.last_policy["document_rag_reason"], "info_query")

    def test_vector_knowledge_agent_enables_document_rag_for_explanation_request(self):
        agent = VectorKnowledgeAgent()

        results = agent.retrieve("座椅加热怎么用", command_type=CommandType.UNKNOWN)

        self.assertTrue(
            any(item.document.metadata.get("knowledge_type") == "document_rag" for item in results)
        )
        self.assertTrue(agent.last_policy["document_rag_enabled"])
        self.assertEqual(agent.last_policy["document_rag_reason"], "explanation_request")


if __name__ == "__main__":
    unittest.main()
