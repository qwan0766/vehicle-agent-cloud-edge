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
    graph.add_node("trip_plan", node_handlers["trip_plan"])
    graph.add_node("decision", node_handlers["decision"])
    graph.add_node("assemble", node_handlers["assemble"])

    graph.add_edge(START, "profile")
    graph.add_edge("profile", "knowledge")
    graph.add_conditional_edges(
        "knowledge",
        lambda state: (
            "route_preference"
            if requires_trip_planning(state["message"].command_type)
            else "decision"
        ),
        {
            "route_preference": "route_preference",
            "decision": "decision",
        },
    )
    graph.add_edge("route_preference", "ecology")
    graph.add_conditional_edges(
        "ecology",
        lambda state: (
            "trip_plan"
            if requires_trip_planning(state["message"].command_type)
            else "decision"
        ),
        {
            "trip_plan": "trip_plan",
            "decision": "decision",
        },
    )
    graph.add_edge("trip_plan", "decision")
    graph.add_edge("decision", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile().invoke(dict(initial_state))
