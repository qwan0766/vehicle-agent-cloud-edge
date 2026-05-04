import unittest

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


if __name__ == "__main__":
    unittest.main()
