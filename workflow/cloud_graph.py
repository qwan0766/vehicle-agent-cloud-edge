class LangGraphUnavailable(RuntimeError):
    """Raised when the optional LangGraph dependency is not available."""


def import_langgraph_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise LangGraphUnavailable(
            "langgraph is not installed; install optional dependency `langgraph` "
            "and set ENABLE_LANGGRAPH=1 to use StateGraph execution."
        ) from exc
    return StateGraph, START, END


def run_langgraph_cloud_workflow(
    initial_state: dict,
    node_handlers: dict,
    requires_trip_planning,
) -> dict:
    StateGraph, START, END = import_langgraph_graph()
    graph = StateGraph(dict)

    graph.add_node("profile", node_handlers["profile"])
    graph.add_node("knowledge", node_handlers["knowledge"])
    graph.add_node("route_preference", node_handlers["route_preference"])
    graph.add_node("ecology", node_handlers["ecology"])
    graph.add_node("context_parallel", node_handlers["context_parallel"])
    graph.add_node("provider_parallel", node_handlers["provider_parallel"])
    graph.add_node("trip_plan", node_handlers["trip_plan"])
    graph.add_node("decision", node_handlers["decision"])
    graph.add_node("assemble", node_handlers["assemble"])

    graph.add_edge(START, "context_parallel")
    graph.add_conditional_edges(
        "context_parallel",
        lambda state: (
            "provider_parallel"
            if requires_trip_planning(state["message"].command_type)
            else "decision"
        ),
        {
            "provider_parallel": "provider_parallel",
            "decision": "decision",
        },
    )
    graph.add_edge("provider_parallel", "trip_plan")
    graph.add_edge("trip_plan", "decision")
    graph.add_edge("decision", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile().invoke(dict(initial_state))
