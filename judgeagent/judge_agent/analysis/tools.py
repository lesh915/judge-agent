from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .analyzer import analyze_traces
from ..conversation.state import ConversationState
from ..core.config import app_config, conversation_config
from ..core.metrics import enrich_finding, get_metric, metric_sort_key
from ..core.schema import AnalysisResult

APP_DEFAULTS = app_config()["defaults"]
SEVERITY_RANK = conversation_config()["severity_rank"]


def _result_dict(result: AnalysisResult) -> Dict[str, Any]:
    data = result.to_dict()
    data["findings"] = [enrich_finding(finding) for finding in data.get("findings", [])]
    return data


def load_traces(state: ConversationState, traces: Iterable[str], adapter_name: Optional[str] = None) -> Dict[str, Any]:
    adapter_name = adapter_name or APP_DEFAULTS["adapter"]
    trace_list = [str(Path(path)) for path in traces]
    results = [_result_dict(result) for result in analyze_traces(trace_list, adapter_name=adapter_name)]
    state.loaded_traces = trace_list
    state.analysis_results = results
    top = _top_findings(state, limit=1)
    if top:
        run, finding = top[0]
        state.set_focus(run_id=run.get("run_id"), finding_id=finding.get("id"), metric=finding.get("metric"))
    return {
        "tool": "load_traces",
        "trace_count": len(trace_list),
        "run_count": len(results),
        "finding_count": sum(len(result.get("findings", [])) for result in results),
        "focused_metric": state.focused_metric,
    }


def list_runs(state: ConversationState) -> Dict[str, Any]:
    runs = []
    for result in state.analysis_results:
        run = result.get("run") or {}
        runs.append({
            "run_id": run.get("run_id"),
            "gate": result.get("gate"),
            "score": result.get("score"),
            "finding_count": len(result.get("findings", [])),
            "trace": (run.get("artifacts") or {}).get("tracePath"),
        })
    return {"tool": "list_runs", "runs": runs}


def summarize_findings(state: ConversationState) -> Dict[str, Any]:
    gates = Counter(result.get("gate", "unknown") for result in state.analysis_results)
    findings = [finding for _, finding in _all_findings(state)]
    severities = Counter(finding.get("severity", "unknown") for finding in findings)
    categories = Counter(finding.get("metric_category") or finding.get("category") or "unknown" for finding in findings)
    top = [finding for _, finding in _top_findings(state, limit=5)]
    return {
        "tool": "summarize_findings",
        "run_count": len(state.analysis_results),
        "gate_counts": dict(gates),
        "severity_counts": dict(severities),
        "category_counts": dict(categories),
        "top_findings": top,
    }


def get_finding(state: ConversationState, query: Optional[str] = None, *, metric: Optional[str] = None, finding_id: Optional[str] = None, run_id: Optional[str] = None) -> Dict[str, Any]:
    selected = _select_finding(state, query or "", metric=metric, finding_id=finding_id, run_id=run_id)
    if not selected:
        return {"tool": "get_finding", "found": False, "message": "matching finding not found"}
    run, finding = selected
    state.set_focus(run_id=run.get("run_id"), finding_id=finding.get("id"), metric=finding.get("metric"))
    return {"tool": "get_finding", "found": True, "run": run, "finding": finding, "metric": finding.get("metric")}


def get_evidence(state: ConversationState, query: Optional[str] = None) -> Dict[str, Any]:
    found = get_finding(state, query)
    if not found.get("found"):
        return {"tool": "get_evidence", "found": False, "message": found.get("message")}
    finding = found["finding"]
    evidence = [{"finding_id": finding.get("id"), "metric": finding.get("metric"), "item": item} for item in finding.get("evidence", [])]
    state.evidence.extend(evidence)
    return {"tool": "get_evidence", "found": True, "metric": finding.get("metric"), "finding": finding, "evidence": evidence}


def explain_gate(state: ConversationState) -> Dict[str, Any]:
    blocked = [result for result in state.analysis_results if result.get("gate") == "block"]
    warnings = [result for result in state.analysis_results if result.get("gate") == "warning"]
    reasons = []
    for result in blocked + warnings:
        run = result.get("run") or {}
        top = sorted(result.get("findings", []), key=_finding_sort_key, reverse=True)[:3]
        reasons.append({"run_id": run.get("run_id"), "gate": result.get("gate"), "score": result.get("score"), "findings": top})
    return {"tool": "explain_gate", "blocked": len(blocked), "warnings": len(warnings), "reasons": reasons}


def recommend_fix(state: ConversationState, query: Optional[str] = None) -> Dict[str, Any]:
    found = get_finding(state, query)
    if not found.get("found"):
        return {"tool": "recommend_fix", "found": False, "message": found.get("message")}
    finding = found["finding"]
    metric_spec = finding.get("metric_spec") or {}
    return {
        "tool": "recommend_fix",
        "found": True,
        "metric": finding.get("metric"),
        "severity": finding.get("severity"),
        "priority": finding.get("metric_priority"),
        "category": metric_spec.get("category") or finding.get("category"),
        "recommendation": finding.get("recommendation"),
        "evidence": finding.get("evidence", []),
    }


def compare_runs(state: ConversationState) -> Dict[str, Any]:
    runs = list_runs(state)["runs"]
    sorted_runs = sorted(runs, key=lambda run: (run.get("gate") == "block", run.get("gate") == "warning", -(run.get("score") or 0)), reverse=True)
    return {"tool": "compare_runs", "runs": sorted_runs}


def _all_findings(state: ConversationState) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for result in state.analysis_results:
        run = result.get("run") or {}
        for finding in result.get("findings", []):
            pairs.append((run, enrich_finding(finding)))
    return pairs


def _top_findings(state: ConversationState, limit: int) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    return sorted(_all_findings(state), key=lambda pair: _finding_sort_key(pair[1]), reverse=True)[:limit]


def _finding_sort_key(finding: Dict[str, Any]) -> Tuple[int, int, float]:
    severity = SEVERITY_RANK.get(str(finding.get("severity", "")).lower(), 0)
    priority = finding.get("metric_priority")
    priority_score = 100 - int(priority or 99)
    confidence = float(finding.get("confidence") or 0)
    return severity, priority_score, confidence


def _select_finding(state: ConversationState, query: str, *, metric: Optional[str] = None, finding_id: Optional[str] = None, run_id: Optional[str] = None) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    q = (query or "").lower()
    metric = (metric or "").lower() or None
    finding_id = (finding_id or "").lower() or None
    run_id = (run_id or "").lower() or None
    candidates = _all_findings(state)
    focused_metric = str(state.focused_metric or state.focus.get("metric") or "").lower()
    focused_id = str(state.focus.get("finding_id") or "").lower()

    for run, finding in candidates:
        if finding_id and str(finding.get("id", "")).lower() == finding_id:
            return run, finding
        if metric and str(finding.get("metric", "")).lower() == metric:
            return run, finding
        if run_id and str(run.get("run_id", "")).lower() == run_id:
            return run, finding
    for run, finding in candidates:
        if str(finding.get("id", "")).lower() in q:
            return run, finding
    for run, finding in candidates:
        metric_name = str(finding.get("metric", "")).lower()
        if metric_name and metric_name in q:
            return run, finding
    for run, finding in candidates:
        rid = str(run.get("run_id", "")).lower()
        if rid and rid in q:
            return run, finding
    if focused_metric or focused_id:
        for run, finding in candidates:
            if str(finding.get("metric", "")).lower() == focused_metric or str(finding.get("id", "")).lower() == focused_id:
                return run, finding
    top = _top_findings(state, limit=1)
    return top[0] if top else None


def metric_metadata(metric_name: str) -> Dict[str, Any]:
    metric = get_metric(metric_name)
    return metric.to_dict() if metric else {}
