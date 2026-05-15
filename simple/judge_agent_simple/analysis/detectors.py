from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..core.schema import Finding, SimpleAgentRun

REQUIRED_SECTIONS = [
    "Summary",
    "Key Metrics",
    "Anomalies",
    "Evidence",
    "RAG Context",
    "MCP Context",
    "Recommended Actions",
    "Confidence & Limitations",
]


def target_path(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"(/[A-Za-z0-9_./-]+)", text)
    return m.group(1) if m else None


def _new_finding(idx: int, **kwargs: Any) -> Finding:
    return Finding(id=f"JD-{idx:03d}", **kwargs)


class ReferenceWebLogDetector:
    def detect(self, run: SimpleAgentRun) -> List[Finding]:
        findings: List[Finding] = []
        checks = [
            self.output_contract,
            self.validation_path,
            self.wrong_endpoint,
            self.parse_error_handling,
            self.metric_consistency,
            self.rag_mcp_presence,
            self.chat_context,
        ]
        for check in checks:
            findings.extend(check(run, len(findings) + 1))
        return [Finding(id=f"JD-{i:03d}", category=f.category, metric=f.metric, severity=f.severity, confidence=f.confidence, evidence=f.evidence, expected=f.expected, actual=f.actual, recommendation=f.recommendation, location=f.location) for i, f in enumerate(findings, start=1)]

    def output_contract(self, run: SimpleAgentRun, start: int) -> List[Finding]:
        final = run.final_output or ""
        if not final:
            return [_new_finding(start, category="completion", metric="output_contract_compliance", severity="critical", confidence=0.95, evidence=["final_output event is missing or empty"], expected="Final output should be present and follow the markdown contract.", actual="No final output found.", recommendation="Ensure finalization emits final_output after validation.")]
        missing = [section for section in REQUIRED_SECTIONS if f"## {section}" not in final]
        if not missing:
            return []
        return [_new_finding(start, category="prompt", metric="output_contract_compliance", severity="high", confidence=0.95, evidence=[f"Missing sections: {', '.join(missing)}"], expected="Final report contains all required markdown sections.", actual="Final report omitted required sections.", recommendation="Restore OUTPUT_CONTRACT instructions and validate required sections before final_output.", location={"eventType": "final_output"})]

    def validation_path(self, run: SimpleAgentRun, start: int) -> List[Finding]:
        node_names = [e.get("node") for e in run.raw_by_type("node_start")]
        validations = run.raw_by_type("validation_result")
        edges = run.raw_by_type("edge_selected")
        skipped = any(e.get("reason") == "fault_validation_skipped" for e in edges)
        if "validate_findings" in node_names and validations and not skipped:
            return []
        return [_new_finding(start, category="graph", metric="validation_path_coverage", severity="critical", confidence=0.98, evidence=[f"node_start sequence={node_names}", f"validation_result_count={len(validations)}", f"validation_skipped_edge={skipped}"], expected="validate_findings node and validation_result events must run before final output.", actual="Validation path was missing or explicitly skipped.", recommendation="Restore validation edge and block finalization when validation is absent.")]

    def wrong_endpoint(self, run: SimpleAgentRun, start: int) -> List[Finding]:
        expected = target_path(run.user_input)
        if not expected:
            return []
        bad: List[str] = []
        for event in run.raw_by_type("tool_start"):
            if event.get("tool") == "filter_log_records":
                actual = (event.get("arguments") or {}).get("path_pattern")
                if actual and actual != expected:
                    bad.append(f"filter_log_records.path_pattern={actual}, expected={expected}")
        for event in run.raw_by_type("tool_end"):
            if event.get("tool") == "compute_log_metrics":
                for item in (event.get("output") or {}).get("top_paths", []):
                    actual = item.get("path")
                    if actual and actual != expected:
                        bad.append(f"metrics.top_paths contains {actual}, expected {expected}")
        if not bad:
            return []
        return [_new_finding(start, category="tool", metric="target_endpoint_consistency", severity="high", confidence=0.96, evidence=bad, expected=f"All tool arguments and metric paths should use {expected}.", actual="Trace used a different endpoint.", recommendation="Ground filter/query arguments in parsed user request targetPath and add argument validation.")]

    def parse_error_handling(self, run: SimpleAgentRun, start: int) -> List[Finding]:
        findings: List[Finding] = []
        worst: Optional[Tuple[int, int]] = None
        repeated = 0
        for event in run.raw_by_type("tool_end"):
            if event.get("tool") != "parse_access_log":
                continue
            out = event.get("output") or {}
            errors = int(out.get("parse_error_count") or 0)
            total = max(1, int(out.get("total_lines") or 0))
            if errors / total > 0.5:
                repeated += 1
                if worst is None or errors / total > worst[0] / max(1, worst[1]):
                    worst = (errors, total)
        if worst:
            errors, total = worst
            final = (run.final_output or "").lower()
            validation_issues = " ".join(str(v.get("issues", [])) for v in run.validation_results).lower()
            reflected = "parse" in final or "parse" in validation_issues
            actual = "High parse error rate was mentioned only as a limitation." if reflected else "Parse errors were not reflected."
            findings.append(_new_finding(start, category="tool", metric="parse_error_handling_score", severity="high", confidence=0.94, evidence=[f"parse_error_count={errors}, total_lines={total}", f"high_parse_error_events={repeated}", f"reflected_in_report_or_validation={reflected}"], expected="High parse error rate should stop or explicitly downgrade the analysis, not continue as a normal successful report.", actual=actual, recommendation="Treat high parse error ratio as a validation failure and prevent confident final reports."))
        return findings

    def metric_consistency(self, run: SimpleAgentRun, start: int) -> List[Finding]:
        metrics_from_tool = [e for e in run.raw_by_type("tool_end") if e.get("tool") == "compute_log_metrics"]
        compute_steps = [e for e in run.raw_by_type("react_step") if e.get("action") == "compute_log_metrics"]
        if compute_steps and not metrics_from_tool:
            return [_new_finding(start, category="completion", metric="metric_result_consistency", severity="high", confidence=0.9, evidence=["react_step selected compute_log_metrics but no tool_end(compute_log_metrics) event exists."], expected="Computed metrics should come from a tool_end event or equivalent verifiable state.", actual="Metric computation was not observable as a tool result.", recommendation="Emit tool_start/tool_end for metric calculation and compare final claims to tool output.")]
        for event in run.raw_by_type("node_end") + run.raw_by_type("node_start"):
            state = event.get("state_after") or event.get("state_before") or {}
            metrics = state.get("metrics") or {}
            if metrics.get("faultInjected"):
                return [_new_finding(start, category="completion", metric="metric_result_consistency", severity="high", confidence=0.98, evidence=[f"faultInjected metrics observed in node {event.get('node')}: {metrics}"], expected="Metrics should be computed from filtered log records.", actual="Injected or unverifiable metrics were used.", recommendation="Reject metrics not produced by compute_log_metrics tool output.")]
        return []

    def rag_mcp_presence(self, run: SimpleAgentRun, start: int) -> List[Finding]:
        findings: List[Finding] = []
        final = run.final_output or ""
        retrieved = any(e.get("tool") == "retrieve_runbook" for e in run.raw_by_type("tool_end"))
        mcp = any(e.get("type") == "mcp_end" and e.get("method") == "tools/call" for e in run.raw_events)
        if not retrieved:
            findings.append(_new_finding(start, category="context", metric="rag_context_presence_and_usage", severity="medium", confidence=0.85, evidence=["No tool_end(retrieve_runbook) event found."], expected="RAG runbook retrieval should occur for incident analysis.", actual="RAG context missing.", recommendation="Call retrieve_runbook before final report."))
        if not mcp:
            findings.append(_new_finding(start + len(findings), category="context", metric="mcp_context_presence_and_usage", severity="medium", confidence=0.85, evidence=["No mcp_end tools/call event found."], expected="MCP service metadata should be fetched for owner/SLO/dependency context.", actual="MCP context missing.", recommendation="Call get_service_context before final report."))
        if retrieved and "## RAG Context" not in final:
            findings.append(_new_finding(start + len(findings), category="context", metric="rag_context_presence_and_usage", severity="medium", confidence=0.8, evidence=["RAG retrieved but final report lacks RAG Context section."], expected="Final report should separate RAG context from measured evidence.", actual="RAG context not surfaced.", recommendation="Preserve RAG Context section in output contract."))
        if mcp and "## MCP Context" not in final:
            findings.append(_new_finding(start + len(findings), category="context", metric="mcp_context_presence_and_usage", severity="medium", confidence=0.8, evidence=["MCP context fetched but final report lacks MCP Context section."], expected="Final report should include MCP Context section.", actual="MCP context not surfaced.", recommendation="Preserve MCP Context section in output contract."))
        return findings

    def chat_context(self, run: SimpleAgentRun, start: int) -> List[Finding]:
        if not any((e.get("type") or "").startswith("chat_") for e in run.raw_events):
            return []
        invoked = bool(run.raw_by_type("chat_analysis_invoked"))
        context_events = run.raw_by_type("chat_context_built")
        responses = run.raw_by_type("chat_response_generated")
        findings: List[Finding] = []
        for event in context_events:
            if not event.get("has_last_analysis") and invoked:
                findings.append(_new_finding(start, category="context", metric="chat_context_grounding", severity="medium", confidence=0.82, evidence=["chat_context_built has_last_analysis=false after analysis invocation."], expected="Follow-up responses should use last_analysis context.", actual="Context builder did not expose last_analysis.", recommendation="Persist analysis summary before follow-up turns."))
        if responses and not invoked and not context_events:
            findings.append(_new_finding(start + len(findings), category="context", metric="chat_context_grounding", severity="low", confidence=0.7, evidence=["Chat response generated without analysis invocation or context build."], expected="Chat responses should be classified and grounded in session context or ask clarification.", actual="No context evidence available.", recommendation="Emit chat_context_built for follow-up responses."))
        return findings


def score_findings(findings: List[Finding]) -> int:
    penalty = {"critical": 30, "high": 15, "medium": 7, "low": 2}
    return max(0, 100 - sum(penalty.get(f.severity, 0) for f in findings))


def gate_for(score: int, findings: List[Finding]) -> str:
    severities = {f.severity for f in findings}
    if "critical" in severities or score < 70:
        return "block"
    if "high" in severities or score < 85:
        return "warning"
    return "pass"
