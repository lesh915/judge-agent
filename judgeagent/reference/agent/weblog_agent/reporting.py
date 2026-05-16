from __future__ import annotations


def build_report(state) -> str:
    metrics = state.metrics or {}
    anomalies = state.anomalies or []
    evidence = state.evidence or {"logLines": [], "metricRefs": []}
    rag_docs = state.ragContext or []
    mcp = state.mcpContext or {}
    target = state.request.get("targetPath") or "requested target"
    limitations = []
    if state.rawLogs and state.rawLogs.get("truncated"):
        limitations.append("Input log was truncated; metrics are based on the sampled lines only.")
    if state.errors:
        limitations.extend(state.errors)
    parse_error_count = state.metrics.get("parse_error_count") if state.metrics else None
    if parse_error_count:
        limitations.append(f"Parse errors were observed: {parse_error_count} lines.")
    if not rag_docs:
        limitations.append("RAG runbook context was not available.")
    if not mcp:
        limitations.append("MCP service metadata was not available.")
    if not limitations:
        limitations.append("No major data limitations were detected in this fixture run.")

    anomaly_lines = []
    for a in anomalies:
        anomaly_lines.append(f"- **{a['type']}** ({a['severity']}): {a['metric']}={a['actual']} expected={a.get('expected')} — {a['reason']}")
    if not anomaly_lines:
        anomaly_lines.append("- No threshold-based anomalies detected.")

    evidence_lines = [f"- `{line}`" for line in evidence.get("logLines", [])[:5]] or ["- No representative log lines were available."]
    metric_refs = [f"- {ref}" for ref in evidence.get("metricRefs", [])] or ["- Metrics were computed from filtered log records."]
    rag_lines = [f"- {doc.get('source')}/{doc.get('doc_id')}: {doc.get('content', '').splitlines()[0]}" for doc in rag_docs[:3]] or ["- No runbook documents retrieved."]
    mcp_lines = [
        f"- service: {mcp.get('service', 'unknown')}",
        f"- owner: {mcp.get('owner', 'unknown')}",
        f"- recentDeployments: {', '.join(mcp.get('recentDeployments', [])) or 'none'}",
        f"- dependencies: {', '.join(mcp.get('dependencies', [])) or 'unknown'}",
        f"- slo: {mcp.get('slo', {})}",
    ] if mcp else ["- No MCP service context available."]

    likely = "- Hypothesis: upstream service or dependency instability may be contributing; verify with service-specific logs."
    if rag_docs:
        likely += "\n- Runbook-backed hypothesis: check auth provider/session store/deployment health before concluding root cause."
    if not anomalies:
        likely = "- No likely cause identified because no anomaly was detected."

    return f"""## Summary

Analyzed web logs for `{target}` using a ReAct agent flow with tools, RAG, and MCP context. Request count was {metrics.get('request_count', 0)} and error rate was {metrics.get('error_rate', 0.0):.2%}.

## Key Metrics

- request_count: {metrics.get('request_count', 0)}
- error_count: {metrics.get('error_count', 0)}
- 5xx_count: {metrics.get('5xx_count', 0)}
- error_rate: {metrics.get('error_rate', 0.0):.2%}
- p95_latency_ms: {metrics.get('p95_latency_ms', 0)}

## Anomalies

{chr(10).join(anomaly_lines)}

## Evidence

Representative log lines:

{chr(10).join(evidence_lines)}

Metric references:

{chr(10).join(metric_refs)}

## RAG Context

{chr(10).join(rag_lines)}

## MCP Context

{chr(10).join(mcp_lines)}

## Likely Causes

{likely}

## Recommended Actions

- Check recent changes and dependency health for `{target}`.
- Compare with service logs and infrastructure metrics.
- Use MCP owner metadata to route follow-up to the responsible service team.
- Continue monitoring error rate and p95 latency.

## Confidence & Limitations

- Confidence: {'medium' if anomalies else 'low'} based on available fixture logs, computed metrics, RAG context, and MCP metadata.
{chr(10).join(f'- {x}' for x in limitations)}
"""
