from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from .agent import HybridConversationAgent, ToolBasedConversationAgent
from .state import ConversationState
from ..llm.clients import LlmClient


class GraphRuntimeState(TypedDict, total=False):
    state: ConversationState
    user_input: str
    plan: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    deterministic_response: str
    final_response: str
    runtime: str
    fallback_reason: str


def langgraph_available() -> bool:
    try:
        import langgraph  # noqa: F401
        return True
    except Exception:
        return False


class GraphConversationAgent(HybridConversationAgent):
    """Optional LangGraph-backed conversation runtime.

    The public behavior matches HybridConversationAgent, but the turn execution
    can be routed through a LangGraph StateGraph when the optional dependency is
    installed. When LangGraph is absent, it falls back to the same deterministic
    tool execution + optional LLM synthesis path and records the fallback in the
    session plan.
    """

    def __init__(self, state: ConversationState, llm: Optional[LlmClient] = None, *, require_langgraph: bool = False):
        super().__init__(state, llm=llm)
        self.require_langgraph = require_langgraph
        self._compiled_graph = None
        self.graph_runtime = "langgraph" if langgraph_available() else "fallback"
        if self.graph_runtime == "langgraph":
            self._compiled_graph = self._build_graph()
        elif require_langgraph:
            raise RuntimeError("LangGraph is not installed. Install with `pip install -e .[agent]` or use --mode hybrid.")

    def welcome(self) -> str:
        base = super().welcome()
        if self.graph_runtime == "langgraph":
            return base + "\n\nGraph mode: LangGraph StateGraph runtime으로 turn을 실행합니다."
        return base + "\n\nGraph mode fallback: LangGraph가 설치되지 않아 hybrid runtime으로 실행합니다."

    def handle_user_turn(self, user_input: str) -> str:
        if self._compiled_graph is None:
            response = super().handle_user_turn(user_input)
            self.state.plan.append({"runtime": "graph-fallback", "reason": "langgraph_not_installed"})
            return response
        graph_state: GraphRuntimeState = {"state": self.state, "user_input": user_input, "runtime": "langgraph"}
        result = self._compiled_graph.invoke(graph_state)
        return result["final_response"]

    def _build_graph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:  # pragma: no cover - guarded by langgraph_available
            return None

        graph = StateGraph(GraphRuntimeState)
        graph.add_node("receive", self._node_receive)
        graph.add_node("plan", self._node_plan)
        graph.add_node("execute_tools", self._node_execute_tools)
        graph.add_node("respond", self._node_respond)
        graph.add_node("save", self._node_save)
        graph.add_edge(START, "receive")
        graph.add_edge("receive", "plan")
        graph.add_edge("plan", "execute_tools")
        graph.add_edge("execute_tools", "respond")
        graph.add_edge("respond", "save")
        graph.add_edge("save", END)
        return graph.compile()

    def _node_receive(self, graph_state: GraphRuntimeState) -> GraphRuntimeState:
        state = graph_state["state"]
        user_input = graph_state["user_input"]
        state.add_message("user", user_input)
        return graph_state

    def _node_plan(self, graph_state: GraphRuntimeState) -> GraphRuntimeState:
        plan = self._plan(graph_state["user_input"])
        graph_state["plan"] = plan
        graph_state["state"].plan = plan
        return graph_state

    def _node_execute_tools(self, graph_state: GraphRuntimeState) -> GraphRuntimeState:
        user_input = graph_state["user_input"]
        results: List[Dict[str, Any]] = []
        for step in graph_state.get("plan", []):
            result = self._execute_step(step, user_input)
            results.append(result)
            graph_state["state"].record_tool(step["tool"], step.get("arguments", {}), result)
        graph_state["tool_results"] = results
        return graph_state

    def _node_respond(self, graph_state: GraphRuntimeState) -> GraphRuntimeState:
        user_input = graph_state["user_input"]
        plan = graph_state.get("plan", [])
        results = graph_state.get("tool_results", [])
        response = self._respond(user_input, plan, results)
        graph_state["final_response"] = response
        graph_state["state"].final_response = response
        return graph_state

    def _node_save(self, graph_state: GraphRuntimeState) -> GraphRuntimeState:
        graph_state["state"].add_message("assistant", graph_state.get("final_response", ""))
        return graph_state
