from __future__ import annotations

from typing import Any, Dict

from .graph import WebLogAnalysisAgent
from .state import WebLogAnalysisState


def build_langgraph_app(agent: WebLogAnalysisAgent):
    """Build an actual LangGraph app when langgraph is installed.

    The default CLI uses the dependency-light runner so fixtures work in a clean
    CI environment. This adapter shows the equivalent production LangGraph shape
    for teams that install `judge-agent-reference[agent]`.
    """

    try:
        from langgraph.graph import END, StateGraph
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("Install optional dependencies with `pip install -e .[agent]` to build the LangGraph app") from exc

    graph = StateGraph(WebLogAnalysisState)

    graph.add_node("initialize_agent", lambda state: _run_node(agent.initialize_agent, state))
    graph.add_node("react_agent", lambda state: _run_node(agent.react_agent, state))
    graph.add_node("validate_findings", lambda state: _run_node(agent.validate_findings, state))
    graph.add_node("finalize", lambda state: _run_node(agent.finalize, state))

    graph.set_entry_point("initialize_agent")
    graph.add_edge("initialize_agent", "react_agent")
    graph.add_edge("react_agent", "validate_findings")
    graph.add_edge("validate_findings", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def _run_node(fn, state: WebLogAnalysisState) -> WebLogAnalysisState:
    fn(state)
    return state
