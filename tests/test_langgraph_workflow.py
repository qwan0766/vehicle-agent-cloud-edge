import unittest
from unittest.mock import patch

import workflow.cloud_graph as cloud_graph
from agents.orchestrator.global_dispatch_agent import GlobalDispatchAgent
from core.constants import CommandType, NetworkStatus, SafetyLevel
from core.message import Message


def make_message(content="导航去蔚来中心", command_type=CommandType.NAVIGATION):
    return Message.create(
        user_id="user_001",
        command_type=command_type,
        safety=SafetyLevel.SAFE,
        content=content,
        network=NetworkStatus.ONLINE,
    )


class FakeCompiledGraph:
    def __init__(self, graph):
        self.graph = graph

    def invoke(self, state):
        current = self.graph.start_target
        payload = dict(state)
        while current != self.graph.end:
            payload = self.graph.nodes[current](payload)
            if current in self.graph.conditional_edges:
                router, mapping = self.graph.conditional_edges[current]
                current = mapping[router(payload)]
            else:
                current = self.graph.edges[current]
        return payload


class FakeStateGraph:
    def __init__(self, state_type):
        self.state_type = state_type
        self.nodes = {}
        self.edges = {}
        self.conditional_edges = {}
        self.start = "__start__"
        self.end = "__end__"
        self.start_target = ""

    def add_node(self, name, handler):
        self.nodes[name] = handler

    def add_edge(self, source, target):
        if source == self.start:
            self.start_target = target
        else:
            self.edges[source] = target

    def add_conditional_edges(self, source, router, mapping):
        self.conditional_edges[source] = (router, mapping)

    def compile(self):
        return FakeCompiledGraph(self)


class TestLangGraphWorkflow(unittest.TestCase):
    def test_default_dispatch_attempts_langgraph_and_falls_back_when_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(
                cloud_graph,
                "import_langgraph_graph",
                side_effect=cloud_graph.LangGraphUnavailable("langgraph not installed"),
            ):
                agent = GlobalDispatchAgent()
                result = agent.dispatch(make_message())

        graph = agent.get_last_graph()
        self.assertTrue(graph["enabled"])
        self.assertEqual(graph["mode"], "lightweight")
        self.assertTrue(graph["fallback"])
        self.assertIn("langgraph not installed", graph["reason"])
        self.assertEqual(
            graph["path"],
            [
                "context_parallel",
                "provider_parallel",
                "trip_plan",
                "decision",
                "assemble",
            ],
        )
        self.assertEqual(
            graph["parallel_groups"],
            [
                {
                    "id": "cloud_context",
                    "label": "云端并行上下文收集",
                    "nodes": ["profile", "knowledge", "route_preference"],
                },
                {
                    "id": "route_provider_parallel",
                    "label": "云端并行生态与路线工具",
                    "nodes": ["ecology", "route_provider"],
                }
            ],
        )
        self.assertNotIn("用户偏好", result)
        self.assertTrue(result)

    def test_langgraph_can_be_disabled_by_env(self):
        with patch.dict("os.environ", {"ENABLE_LANGGRAPH": "0"}, clear=True):
            with patch.object(
                cloud_graph,
                "import_langgraph_graph",
                side_effect=AssertionError("langgraph import should not be attempted"),
            ):
                agent = GlobalDispatchAgent()
                agent.dispatch(make_message())

        graph = agent.get_last_graph()
        self.assertFalse(graph["enabled"])
        self.assertEqual(graph["mode"], "lightweight")
        self.assertFalse(graph["fallback"])

    def test_langgraph_enabled_without_dependency_falls_back_to_lightweight(self):
        with patch.dict("os.environ", {"ENABLE_LANGGRAPH": "1"}, clear=True):
            with patch.object(
                cloud_graph,
                "import_langgraph_graph",
                side_effect=cloud_graph.LangGraphUnavailable("langgraph not installed"),
            ):
                agent = GlobalDispatchAgent()
                agent.dispatch(make_message("温度调到24度", CommandType.CAR_CONTROL))

        graph = agent.get_last_graph()
        self.assertEqual(graph["mode"], "lightweight")
        self.assertTrue(graph["fallback"])
        self.assertIn("langgraph not installed", graph["reason"])
        self.assertNotIn("trip_plan", graph["path"])
        self.assertEqual(
            graph["parallel_groups"],
            [
                {
                    "id": "cloud_context",
                    "label": "云端并行上下文收集",
                    "nodes": ["profile", "knowledge"],
                }
            ],
        )

    def test_default_dispatch_uses_state_graph_when_available(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(
                cloud_graph,
                "import_langgraph_graph",
                return_value=(FakeStateGraph, "__start__", "__end__"),
            ):
                agent = GlobalDispatchAgent()
                agent.dispatch(make_message())

        graph = agent.get_last_graph()
        self.assertEqual(graph["mode"], "langgraph")
        self.assertFalse(graph["fallback"])
        self.assertEqual(graph["backend"], "StateGraph")
        self.assertIn("context_parallel", graph["path"])
        self.assertIn("provider_parallel", graph["path"])
        self.assertIn("trip_plan", graph["path"])


if __name__ == "__main__":
    unittest.main()
