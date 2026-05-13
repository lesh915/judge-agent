from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from . import tools
from .llm import LLMClient, parse_json_object
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
    def __init__(self, trace_logger: TraceLogger, fault: Optional[str] = None, llm: Optional[LLMClient] = None, use_llm: bool = True):
        self.trace = trace_logger
        self.fault = fault
        self.llm = llm or LLMClient()
        self.use_llm = use_llm

    def run(self, user_input: str, access_log_path: str, baseline_path: Optional[str] = None, log_format: str = "nginx_combined") -> WebLogAnalysisState:
        state = WebLogAnalysisState()
        state.request["rawUserInput"] = user_input
        state.logSource = {"accessLogPath": access_log_path, "format": log_format}
        self.trace.emit("run_start", agent_name="weblog-analysis-agent", agent_version="0.2.0", framework="langgraph", graph_version="0.2.0", user_input=user_input, llm_enabled=bool(self.use_llm and self.llm.enabled), llm_model=self.llm.config.model)
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

    def _llm_call(self, name: str, messages, response_format=None) -> Optional[Dict[str, Any]]:
        event_id = f"llm-{name}"
        if not self.use_llm:
            self.trace.emit("llm_skipped", event_id=event_id, name=name, reason="disabled_by_cli")
            return None
        if not self.llm.enabled:
            self.trace.emit("llm_skipped", event_id=event_id, name=name, reason=f"missing_{self.llm.config.api_key_env}", model=self.llm.config.model)
            return None
        self.trace.emit("llm_start", event_id=event_id, name=name, model=self.llm.config.model, messages=messages)
        try:
            result = self.llm.chat(messages, response_format=response_format)
            self.trace.emit("llm_end", event_id=event_id, name=name, model=result.get("model"), output=result.get("content"), usage=result.get("usage"), latency_ms=result.get("latency_ms"))
            return result
        except Exception as exc:
            self.trace.emit("llm_error", event_id=event_id, name=name, model=self.llm.config.model, error={"type": exc.__class__.__name__, "message": str(exc)})
            return None

    def parse_request(self, state):
        fallback = parse_request_text(state.request["rawUserInput"])
        result = self._llm_call("parse_request", [
            {"role": "system", "content": SYSTEM_PROMPT + "\nExtract the user's log-analysis intent as JSON only."},
            {"role": "user", "content": f"User request: {state.request['rawUserInput']}\nReturn JSON with targetPath, requestedMetrics, statusMin, statusMax, statusFocus."},
        ], response_format={"type": "json_object"})
        if result:
            try:
                parsed = parse_json_object(result["content"])
                state.request.update({**fallback, **{k: v for k, v in parsed.items() if v is not None}})
                return
            except Exception as exc:
                state.errors.append(f"LLM request parsing failed; used fallback parser: {exc}")
        state.request.update(fallback)

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
        issues = []
        if not state.metrics:
            issues.append("metrics_missing")
        if state.anomalies and not state.evidence.get("logLines"):
            issues.append("anomalies_missing_log_evidence")
        if state.metrics.get("parse_error_count", 0) and not state.errors and self.fault != "parse_error_ignored":
            issues.append("parse_errors_present")
        state.validation = {"passed": not issues, "issues": issues}
        self.trace.emit("validation_result", event_id="validation-pre-report", passed=state.validation["passed"], checks=["metrics_present", "anomalies_have_evidence", "analysis_state_consistent"], issues=state.validation["issues"])

    def generate_report(self, state):
        if self.fault == "prompt_output_contract":
            state.finalReport = "## Summary\n\n/api/login is failing because of a database migration. Immediate rollback is required."
        elif not state.finalReport:
            summary = {
                "request": state.request,
                "metrics": state.metrics,
                "anomalies": state.anomalies,
                "evidence": state.evidence,
                "validation": state.validation,
                "errors": state.errors,
                "rawLogs": None if not state.rawLogs else {"lineCount": state.rawLogs.get("lineCount"), "truncated": state.rawLogs.get("truncated")},
            }
            result = self._llm_call("generate_report", [
                {"role": "system", "content": SYSTEM_PROMPT + "\n" + TOOL_POLICY + "\n" + OUTPUT_CONTRACT},
                {"role": "user", "content": "Generate the final markdown report from this verified analysis state. Do not invent metrics or causes.\n" + json.dumps(summary, ensure_ascii=False)},
            ])
            if result and result.get("content", "").strip():
                state.finalReport = result["content"].strip()
            else:
                state.finalReport = build_report(state)
        state.validation = validate_state(state)
        self.trace.emit("validation_result", event_id="validation-final", passed=state.validation["passed"], checks=["metrics_present", "anomalies_have_evidence", "report_matches_tool_results", "output_contract"], issues=state.validation["issues"])

    def handle_error(self, state):
        state.validation = {"passed": False, "issues": state.errors[:]} 
