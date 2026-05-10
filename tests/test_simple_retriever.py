import unittest

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


if __name__ == "__main__":
    unittest.main()
