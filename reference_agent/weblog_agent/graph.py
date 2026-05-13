from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from . import tools
from .prompts import OUTPUT_CONTRACT, SYSTEM_PROMPT, TOOL_POLICY
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
    return {
        "rawUserInput": text,
        "targetPath": path_match.group(1) if path_match else None,
        "requestedMetrics": metrics or ["error_rate"],
        "statusMin": 0,
        "statusMax": 599,
        "statusFocus": "5xx" if "5xx" in text.lower() else None,
    }


class WebLogAnalysisAgent:
    def __init__(self, trace_logger: TraceLogger, fault: Optional[str] = None):
        self.trace = trace_logger
        self.fault = fault

    def run(self, user_input: str, access_log_path: str, baseline_path: Optional[str] = None, log_format: str = "nginx_combined") -> WebLogAnalysisState:
        state = WebLogAnalysisState()
        state.request["rawUserInput"] = user_input
        state.logSource = {"accessLogPath": access_log_path, "format": log_format}
        self.trace.emit("run_start", agent_name="weblog-analysis-agent", agent_version="0.1.0", framework="langgraph", graph_version="0.1.0", user_input=user_input)
        self.trace.emit("instruction_snapshot", system=SYSTEM_PROMPT, tool_policy=TOOL_POLICY, output_contract=OUTPUT_CONTRACT)
        try:
            self._node("parse_request", state, self.parse_request)
            self._edge("parse_request", "load_logs", "request_parsed")
            self._node("load_logs", state, self.load_logs)
            self._edge("load_logs", "parse_logs", "logs_loaded")
            self._node("parse_logs", state, self.parse_logs)
            self._edge("parse_logs", "filter_logs", "logs_parsed")
            self._node("filter_logs", state, self.filter_logs)
            self._edge("filter_logs", "compute_metrics", "records_filtered")
            if self.fault == "metric_hallucination":
                state.metrics = {"request_count": len(state.filteredRecords), "error_count": 124, "5xx_count": 124, "error_rate": 0.124, "p95_latency_ms": 0}
            else:
                self._node("compute_metrics", state, self.compute_metrics)
            self._edge("compute_metrics", "detect_anomalies", "metrics_computed")
            self._node("detect_anomalies", state, self.detect_anomalies)
            self._edge("detect_anomalies", "collect_evidence", "anomalies_found" if state.anomalies else "no_anomalies")
            self._node("collect_evidence", state, self.collect_evidence)
            if self.fault != "validation_skipped":
                self._edge("collect_evidence", "validate_findings", "evidence_collected")
                self._node("validate_findings", state, self.validate_findings)
                self._edge("validate_findings", "generate_report", "validation_completed")
            else:
                self._edge("collect_evidence", "generate_report", "fault_validation_skipped")
            self._node("generate_report", state, self.generate_report)
        except Exception as exc:
            state.errors.append(str(exc))
            self._edge("error", "handle_error", "exception")
            self._node("handle_error", state, self.handle_error)
            self._edge("handle_error", "generate_report", "error_report")
            self._node("generate_report", state, self.generate_report)
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
            self.trace.tool_end(eid, name, {k: v for k, v in out.items() if k != "lines" and k != "records"})
            return out
        except Exception as exc:
            self.trace.tool_error(eid, name, {"message": str(exc), "type": exc.__class__.__name__})
            raise

    def parse_request(self, state):
        state.request.update(parse_request_text(state.request["rawUserInput"]))

    def load_logs(self, state):
        out = self._tool("read_log_file", tools.read_log_file, {"path": state.logSource["accessLogPath"], "max_lines": 10000})
        state.rawLogs = {"lines": out["lines"], "lineCount": out["line_count"], "truncated": out["truncated"]}

    def parse_logs(self, state):
        lines = state.rawLogs["lines"] if state.rawLogs else []
        if self.fault == "parse_error_ignored":
            lines = ["not a valid log line"] * max(10, len(lines))
        out = self._tool("parse_access_log", tools.parse_access_log, {"lines": lines, "format": state.logSource.get("format", "nginx_combined")})
        state.parsedRecords = out["records"]
        state.metrics["parse_error_count"] = out["parse_error_count"]
        if out["parse_error_count"] and out["parse_error_count"] / max(1, out["total_lines"]) > 0.5 and self.fault != "parse_error_ignored":
            state.errors.append("High parse error rate; analysis may be unreliable.")

    def filter_logs(self, state):
        path = state.request.get("targetPath")
        if self.fault == "wrong_endpoint":
            path = "/api/payment"
        out = self._tool("filter_log_records", tools.filter_log_records, {
            "records": state.parsedRecords,
            "path_pattern": path,
            "status_min": state.request.get("statusMin", 0),
            "status_max": state.request.get("statusMax", 599),
        })
        state.filteredRecords = out["records"]

    def compute_metrics(self, state):
        out = self._tool("compute_log_metrics", tools.compute_log_metrics, {"records": state.filteredRecords, "group_by": ["path", "status", "ip"], "latency_percentiles": [50, 95, 99]})
        parse_errors = state.metrics.get("parse_error_count", 0)
        state.metrics = {**out, "parse_error_count": parse_errors}

    def detect_anomalies(self, state):
        out = self._tool("detect_log_anomalies", tools.detect_log_anomalies, {"metrics": state.metrics, "baseline": state.baseline, "thresholds": {"error_rate_warning": 0.05, "error_rate_critical": 0.10, "p95_latency_warning_ms": 1000}})
        state.anomalies = out["anomalies"]

    def collect_evidence(self, state):
        lines = [r.get("raw", "") for r in state.filteredRecords if int(r.get("status", 0)) >= 500][:5]
        state.evidence = {
            "logLines": lines,
            "metricRefs": [f"error_rate={state.metrics.get('error_rate', 0.0)}", f"request_count={state.metrics.get('request_count', 0)}"],
        }

    def validate_findings(self, state):
        state.finalReport = build_report(state)
        state.validation = validate_state(state)
        self.trace.emit("validation_result", event_id="validation-001", passed=state.validation["passed"], checks=["metrics_present", "anomalies_have_evidence", "report_matches_tool_results"], issues=state.validation["issues"])

    def generate_report(self, state):
        if self.fault == "prompt_output_contract":
            state.finalReport = "## Summary\n\n/api/login is failing because of a database migration. Immediate rollback is required."
        elif not state.finalReport:
            state.finalReport = build_report(state)

    def handle_error(self, state):
        state.validation = {"passed": False, "issues": state.errors[:]} 
