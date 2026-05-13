from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from . import tools
from .llm import LLMClient, parse_json_object
from .mcp import StdioMCPClient
from .prompts import OUTPUT_CONTRACT, REACT_PROTOCOL, SYSTEM_PROMPT, TOOL_POLICY
from .rag import LocalRunbookRetriever
from .reporting import build_report
from .state import WebLogAnalysisState
from .trace import TraceLogger
from .validation import validate_state


def parse_request_text(text: str) -> Dict[str, Any]:
    path_match = re.search(r"(/[A-Za-z0-9_./-]+)", text)
    metrics = []
    if "에러" in text or "error" in text.lower() or "5xx" in text.lower():
        metrics.append("error_rate")
    if "latency" in text.lower() or "지연" in text:
        metrics.append("latency")
    status_min, status_max = 0, 599
    return {
        "rawUserInput": text,
        "targetPath": path_match.group(1) if path_match else None,
        "requestedMetrics": metrics or ["error_rate"],
        "statusMin": status_min,
        "statusMax": status_max,
        "statusFocus": "5xx" if "5xx" in text.lower() else None,
    }


class WebLogAnalysisAgent:
    """LangGraph/LangChain-style ReAct reference agent.

    The production target for Judge Agent is a normal AI agent composed of LLM,
    prompts, tools, MCP and RAG. This reference implementation keeps the runtime
    dependency-light for CI, but its graph, prompts, ReAct loop and trace events
    mirror the shape Judge Agent should observe from a LangGraph ReAct agent.
    """

    def __init__(
        self,
        trace_logger: TraceLogger,
        fault: Optional[str] = None,
        llm: Optional[LLMClient] = None,
        use_llm: bool = True,
        retriever: Optional[LocalRunbookRetriever] = None,
        mcp_client: Optional[StdioMCPClient] = None,
        max_steps: int = 10,
    ):
        self.trace = trace_logger
        self.fault = fault
        self.llm = llm or LLMClient()
        self.use_llm = use_llm
        self.retriever = retriever or LocalRunbookRetriever()
        self.mcp = mcp_client or StdioMCPClient()
        self.max_steps = max_steps

    def run(self, user_input: str, access_log_path: str, baseline_path: Optional[str] = None, log_format: str = "nginx_combined") -> WebLogAnalysisState:
        state = WebLogAnalysisState()
        state.request["rawUserInput"] = user_input
        state.logSource = {"accessLogPath": access_log_path, "format": log_format}
        self.trace.emit(
            "run_start",
            agent_name="weblog-react-agent",
            agent_version="0.3.0",
            framework="langgraph",
            graph_version="0.3.0",
            architecture="react",
            components=["llm", "prompt", "tools", "mcp", "rag"],
            user_input=user_input,
            llm_enabled=bool(self.use_llm and self.llm.enabled),
            llm_model=self.llm.config.model,
            llm_config=self.llm.config.sanitized(),
        )
        self.trace.emit("instruction_snapshot", system=SYSTEM_PROMPT, react_protocol=REACT_PROTOCOL, tool_policy=TOOL_POLICY, output_contract=OUTPUT_CONTRACT)
        try:
            self._node("initialize_agent", state, self.initialize_agent)
            self._edge("initialize_agent", "react_agent", "agent_initialized")
            self._node("react_agent", state, self.react_agent)
            self._edge("react_agent", "validate_findings", "react_loop_completed")
            if self.fault != "validation_skipped":
                self._node("validate_findings", state, self.validate_findings)
                self._edge("validate_findings", "finalize", "validation_completed")
            else:
                self._edge("react_agent", "finalize", "fault_validation_skipped")
            self._node("finalize", state, self.finalize)
        except Exception as exc:
            state.errors.append(str(exc))
            self._edge("error", "handle_error", "exception")
            self._node("handle_error", state, self.handle_error)
            self._edge("handle_error", "finalize", "error_report")
            self._node("finalize", state, self.finalize)
        finally:
            self.close()
        self.trace.emit("final_output", content=state.finalReport or "")
        self.trace.emit("run_end", status="completed" if not state.errors else "completed_with_errors")
        return state

    def _edge(self, frm: str, to: str, reason: str):
        self.trace.emit("edge_selected", **{"from": frm, "to": to, "reason": reason})

    def _node(self, name: str, state: WebLogAnalysisState, fn):
        eid = self.trace.node_start(name, state.snapshot())
        fn(state)
        self.trace.node_end(eid, name, state.snapshot())

    def _tool(self, name: str, fn, args: Dict[str, Any]):
        eid = self.trace.tool_start(name, args)
        try:
            out = fn(**args)
            redacted = {k: v for k, v in out.items() if k not in {"lines", "records"}}
            self.trace.tool_end(eid, name, redacted)
            return out
        except Exception as exc:
            self.trace.tool_error(eid, name, {"message": str(exc), "type": exc.__class__.__name__})
            raise

    def _mcp_list_tools(self) -> Dict[str, Any]:
        eid = "mcp-tools-list"
        self.trace.emit("mcp_start", event_id=eid, server="weblog-service-context-mcp", method="tools/list", arguments={})
        try:
            out = self.mcp.list_tools()
            self.trace.emit("mcp_end", event_id=eid, server=self.mcp.server_name, method="tools/list", output=out)
            return out
        except Exception as exc:
            self.trace.emit("mcp_error", event_id=eid, server="weblog-service-context-mcp", method="tools/list", error={"type": exc.__class__.__name__, "message": str(exc)})
            raise

    def _mcp_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        eid = f"mcp-tools-call-{name}"
        self.trace.emit("mcp_start", event_id=eid, server="weblog-service-context-mcp", method="tools/call", tool=name, arguments=args)
        try:
            out = self.mcp.call_tool(name, args)
            self.trace.emit("mcp_end", event_id=eid, server=self.mcp.server_name, method="tools/call", tool=name, output=out)
            return out
        except Exception as exc:
            self.trace.emit("mcp_error", event_id=eid, server="weblog-service-context-mcp", method="tools/call", tool=name, error={"type": exc.__class__.__name__, "message": str(exc)})
            raise

    def close(self) -> None:
        close = getattr(self.mcp, "close", None)
        if close:
            close()

    def _llm_call(self, name: str, messages, response_format=None) -> Optional[Dict[str, Any]]:
        event_id = f"llm-{name}-{len(messages)}"
        if not self.use_llm:
            self.trace.emit("llm_skipped", event_id=event_id, name=name, reason="disabled_by_cli")
            return None
        if not self.llm.enabled:
            self.trace.emit("llm_skipped", event_id=event_id, name=name, reason="llm_not_configured_or_missing_api_key", model=self.llm.config.model, config=self.llm.config.sanitized())
            return None
        self.trace.emit("llm_start", event_id=event_id, name=name, model=self.llm.config.model, messages=messages)
        try:
            result = self.llm.chat(messages, response_format=response_format)
            self.trace.emit("llm_end", event_id=event_id, name=name, model=result.get("model"), output=result.get("content"), usage=result.get("usage"), latency_ms=result.get("latency_ms"))
            return result
        except Exception as exc:
            self.trace.emit("llm_error", event_id=event_id, name=name, model=self.llm.config.model, error={"type": exc.__class__.__name__, "message": str(exc)})
            return None

    def initialize_agent(self, state: WebLogAnalysisState):
        mcp_tools = self._mcp_list_tools()
        self.trace.emit("agent_components", llm=self.llm.config.sanitized(), prompt=["SYSTEM_PROMPT", "REACT_PROTOCOL", "TOOL_POLICY", "OUTPUT_CONTRACT"], tools=self.tool_names(), mcp_servers=[self.mcp.server_name], mcp_tools=mcp_tools.get("tools", []), rag={"retriever": "LocalRunbookRetriever"})

    def tool_names(self) -> List[str]:
        return ["parse_user_request", "read_log_file", "parse_access_log", "filter_log_records", "compute_log_metrics", "detect_log_anomalies", "retrieve_runbook", "get_service_context", "collect_evidence", "finish"]

    def react_agent(self, state: WebLogAnalysisState):
        for step_no in range(1, self.max_steps + 1):
            action = self._next_react_action(state, step_no)
            thought = action.get("thought", "")
            name = action.get("action")
            self.trace.emit("react_step", step=step_no, thought=thought, action=name, action_input=action.get("action_input", {}))
            state.reactSteps.append({"step": step_no, "thought": thought, "action": name})
            if name == "finish":
                if action.get("final"):
                    state.finalReport = action["final"]
                return
            observation = self._execute_action(state, name, action.get("action_input") or {})
            self.trace.emit("observation", step=step_no, action=name, observation=self._summarize_observation(observation))
        state.errors.append("ReAct loop exceeded max steps")

    def _next_react_action(self, state: WebLogAnalysisState, step_no: int) -> Dict[str, Any]:
        result = self._llm_call("react_decide", [
            {"role": "system", "content": SYSTEM_PROMPT + "\n" + REACT_PROTOCOL + "\n" + TOOL_POLICY},
            {"role": "user", "content": json.dumps({"step": step_no, "state": state.snapshot(), "availableTools": self.tool_names()}, ensure_ascii=False)},
        ], response_format={"type": "json_object"})
        if result:
            try:
                action = parse_json_object(result["content"])
                if action.get("action") in self.tool_names():
                    return action
            except Exception as exc:
                state.errors.append(f"LLM ReAct decision failed; used fallback policy: {exc}")
        return self._fallback_action(state)

    def _fallback_action(self, state: WebLogAnalysisState) -> Dict[str, Any]:
        if not state.request.get("targetPath"):
            return {"thought": "Need to understand the user's target endpoint and metrics first.", "action": "parse_user_request", "action_input": {"text": state.request["rawUserInput"]}}
        if state.rawLogs is None:
            return {"thought": "Need raw access logs before computing evidence.", "action": "read_log_file", "action_input": {"path": state.logSource["accessLogPath"], "max_lines": 10000}}
        if not state.parsedRecords:
            return {"thought": "Need structured log records for analysis.", "action": "parse_access_log", "action_input": {"format": state.logSource.get("format", "nginx_combined")}}
        if not state.filteredRecords:
            return {"thought": "Need records scoped to the requested endpoint/status range.", "action": "filter_log_records", "action_input": {}}
        if "request_count" not in state.metrics or (self.fault == "metric_hallucination" and "faultInjected" not in state.metrics):
            return {"thought": "Need deterministic metrics from filtered records.", "action": "compute_log_metrics", "action_input": {}}
        anomaly_checked = any(step.get("action") == "detect_log_anomalies" for step in state.reactSteps)
        if not anomaly_checked:
            return {"thought": "Need anomaly detection against thresholds and baseline.", "action": "detect_log_anomalies", "action_input": {}}
        if not state.ragContext:
            return {"thought": "Need runbook context via RAG for likely causes and actions.", "action": "retrieve_runbook", "action_input": {"query": state.request.get("targetPath") or state.request["rawUserInput"]}}
        if not state.mcpContext:
            return {"thought": "Need MCP service metadata for owner, SLO, dependencies, and deployments.", "action": "get_service_context", "action_input": {"path": state.request.get("targetPath")}}
        if not state.evidence.get("logLines"):
            return {"thought": "Need evidence snippets tied to computed metrics.", "action": "collect_evidence", "action_input": {}}
        return {"thought": "All required observations are available; generate final answer.", "action": "finish", "final": self._generate_final_report(state)}

    def _execute_action(self, state: WebLogAnalysisState, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name == "parse_user_request":
            parsed = parse_request_text(args.get("text") or state.request["rawUserInput"])
            state.request.update(parsed)
            return parsed
        if name == "read_log_file":
            out = self._tool("read_log_file", tools.read_log_file, {"path": args.get("path") or state.logSource["accessLogPath"], "max_lines": int(args.get("max_lines", 10000))})
            state.rawLogs = {"lines": out["lines"], "lineCount": out["line_count"], "truncated": out["truncated"]}
            return out
        if name == "parse_access_log":
            lines = state.rawLogs["lines"] if state.rawLogs else []
            if self.fault == "parse_error_ignored":
                lines = ["not a valid log line"] * max(10, len(lines))
            out = self._tool("parse_access_log", tools.parse_access_log, {"lines": lines, "format": args.get("format", state.logSource.get("format", "nginx_combined"))})
            state.parsedRecords = out["records"]
            state.metrics["parse_error_count"] = out["parse_error_count"]
            if out["parse_error_count"] and out["parse_error_count"] / max(1, out["total_lines"]) > 0.5 and self.fault != "parse_error_ignored":
                state.errors.append("High parse error rate; analysis may be unreliable.")
            return out
        if name == "filter_log_records":
            path = state.request.get("targetPath")
            if self.fault == "wrong_endpoint":
                path = "/api/payment"
            out = self._tool("filter_log_records", tools.filter_log_records, {"records": state.parsedRecords, "path_pattern": path, "status_min": state.request.get("statusMin", 0), "status_max": state.request.get("statusMax", 599)})
            state.filteredRecords = out["records"]
            return out
        if name == "compute_log_metrics":
            if self.fault == "metric_hallucination":
                state.metrics = {"request_count": len(state.filteredRecords), "error_count": 124, "5xx_count": 124, "error_rate": 0.124, "p95_latency_ms": 0, "faultInjected": True}
                return state.metrics
            out = self._tool("compute_log_metrics", tools.compute_log_metrics, {"records": state.filteredRecords, "group_by": ["path", "status", "ip"], "latency_percentiles": [50, 95, 99]})
            parse_errors = state.metrics.get("parse_error_count", 0)
            state.metrics = {**out, "parse_error_count": parse_errors}
            return out
        if name == "detect_log_anomalies":
            out = self._tool("detect_log_anomalies", tools.detect_log_anomalies, {"metrics": state.metrics, "baseline": state.baseline, "thresholds": {"error_rate_warning": 0.05, "error_rate_critical": 0.10, "p95_latency_warning_ms": 1000}})
            state.anomalies = out["anomalies"]
            return out
        if name == "retrieve_runbook":
            out = self._tool("retrieve_runbook", self.retriever.retrieve, {"query": args.get("query") or state.request.get("targetPath") or state.request["rawUserInput"], "k": int(args.get("k", 3))})
            state.ragContext = out.get("documents", [])
            return out
        if name == "get_service_context":
            out = self._mcp_call("get_service_context", {"path": args.get("path") or state.request.get("targetPath")})
            state.mcpContext = out
            return out
        if name == "collect_evidence":
            lines = [r.get("raw", "") for r in state.filteredRecords if int(r.get("status", 0)) >= 500][:5]
            state.evidence = {"logLines": lines, "metricRefs": [f"error_rate={state.metrics.get('error_rate', 0.0)}", f"request_count={state.metrics.get('request_count', 0)}"]}
            return state.evidence
        raise ValueError(f"unknown action: {name}")

    def _generate_final_report(self, state: WebLogAnalysisState) -> str:
        if self.fault == "prompt_output_contract":
            return "## Summary\n\n/api/login is failing because of a database migration. Immediate rollback is required."
        result = self._llm_call("final_report", [
            {"role": "system", "content": SYSTEM_PROMPT + "\n" + TOOL_POLICY + "\n" + OUTPUT_CONTRACT},
            {"role": "user", "content": "Generate the final markdown report from this ReAct state. Do not invent metrics or causes.\n" + json.dumps(self._report_state(state), ensure_ascii=False)},
        ])
        if result and result.get("content", "").strip():
            return result["content"].strip()
        return build_report(state)

    def _report_state(self, state: WebLogAnalysisState) -> Dict[str, Any]:
        return {
            "request": state.request,
            "metrics": state.metrics,
            "anomalies": state.anomalies,
            "evidence": state.evidence,
            "ragContext": state.ragContext,
            "mcpContext": state.mcpContext,
            "validation": state.validation,
            "errors": state.errors,
            "rawLogs": None if not state.rawLogs else {"lineCount": state.rawLogs.get("lineCount"), "truncated": state.rawLogs.get("truncated")},
        }

    def _summarize_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in observation.items() if k not in {"lines", "records"}}

    def validate_findings(self, state: WebLogAnalysisState):
        state.validation = validate_state(state)
        self.trace.emit("validation_result", event_id="validation-final", passed=state.validation["passed"], checks=["metrics_present", "anomalies_have_evidence", "rag_context_present", "mcp_context_present", "output_contract"], issues=state.validation["issues"])

    def finalize(self, state: WebLogAnalysisState):
        if not state.finalReport:
            state.finalReport = self._generate_final_report(state)
        state.validation = validate_state(state)
        self.trace.emit("validation_result", event_id="validation-post-finalize", passed=state.validation["passed"], checks=["metrics_present", "anomalies_have_evidence", "rag_context_present", "mcp_context_present", "output_contract"], issues=state.validation["issues"])

    def handle_error(self, state: WebLogAnalysisState):
        state.validation = {"passed": False, "issues": state.errors[:]}
