from __future__ import annotations


def validate_state(state):
    issues = []
    if not state.metrics:
        issues.append("metrics_missing")
    if state.anomalies and not state.evidence.get("logLines"):
        issues.append("anomalies_missing_log_evidence")
    if not state.ragContext:
        issues.append("rag_context_missing")
    if not state.mcpContext:
        issues.append("mcp_context_missing")
    if state.rawLogs and state.rawLogs.get("truncated") and state.finalReport and "truncated" not in state.finalReport.lower():
        issues.append("truncated_logs_without_limitation")
    if state.finalReport:
        required = ["Summary", "Key Metrics", "Anomalies", "Evidence", "RAG Context", "MCP Context", "Recommended Actions", "Confidence & Limitations"]
        for section in required:
            if f"## {section}" not in state.finalReport:
                issues.append(f"missing_section:{section}")
    return {"passed": not issues, "issues": issues}
