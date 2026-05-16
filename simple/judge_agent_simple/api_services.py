from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from reference_agent.weblog_agent.fixtures import fixtures
from reference_agent.weblog_agent.graph import WebLogAnalysisAgent
from reference_agent.weblog_agent.trace import TraceLogger

from .analysis.analyzer import analyze_traces
from .analysis.reporter import markdown_report
from .conversation.agent import HybridConversationAgent, ToolBasedConversationAgent
from .conversation.graph import GraphConversationAgent
from .conversation.state import ConversationState, load_conversation_state, save_conversation_state
from .core.config import app_config, config_dir, llm_profiles_config
from .core.metrics import list_metrics
from .llm.clients import create_llm_client
from .api_models import ApiError, AnalysisRequest, JudgeMessageRequest, JudgeSessionRequest, ReferenceRunRequest
from .api_store import ApiStore, make_id


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if not path.exists():
        return events
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            raw = {"type": "invalid_json", "line": line}
        raw.setdefault("_index", index)
        events.append(raw)
    return events


def _event_counts(path: Path) -> Dict[str, int]:
    return dict(Counter(str(event.get("type") or "unknown") for event in _read_jsonl(path)))


def _timeline_preview(path: Path, limit: int = 100) -> List[Dict[str, Any]]:
    interesting = {"react_step", "tool_start", "tool_end", "mcp_end", "validation_result", "final_output", "chat_response_generated"}
    rows: List[Dict[str, Any]] = []
    for event in _read_jsonl(path):
        event_type = str(event.get("type") or "unknown")
        if event_type not in interesting:
            continue
        title = str(event.get("action") or event.get("tool") or event.get("node") or event.get("method") or event_type)
        detail = str(event.get("thought") or event.get("observation") or event.get("response") or event.get("content") or event.get("status") or "")[:1000]
        rows.append({"index": event.get("_index"), "type": event_type, "title": title, "detail": detail})
        if len(rows) >= limit:
            break
    return rows


def health() -> Dict[str, Any]:
    return {"status": "ok", "version": "0.1.0", "runtime": "file-backed"}


def config_snapshot() -> Dict[str, Any]:
    app = app_config()
    profiles = llm_profiles_config()
    return {
        "configDir": str(config_dir()),
        "appDefaults": app.get("defaults", {}),
        "supported": app.get("supported", {}),
        "llmProfiles": {
            "defaultProvider": profiles.get("default_provider"),
            "defaultModel": profiles.get("default_model"),
            "providers": sorted((profiles.get("providers") or {}).keys()),
        },
        "metrics": {"count": len(list_metrics())},
    }


def metric_list() -> Dict[str, Any]:
    return {"metrics": [metric.to_dict() for metric in list_metrics()]}


def list_reference_fixtures() -> Dict[str, Any]:
    return {
        "fixtures": [
            {
                "id": fixture.id,
                "userInput": fixture.user_input,
                "accessLogPath": str(fixture.access_log_path),
                "fault": fixture.fault,
                "expectedCategory": fixture.expected_category,
            }
            for fixture in fixtures().values()
        ]
    }


def run_reference_agent(request: ReferenceRunRequest, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    store = store or ApiStore()
    store.ensure()
    if request.mode not in {"fixture", "custom-analysis"}:
        raise ApiError("BAD_REQUEST", "Only fixture and custom-analysis modes are implemented in MVP", {"mode": request.mode})

    all_fixtures = fixtures()
    if request.mode == "fixture":
        if not request.fixtureId or request.fixtureId not in all_fixtures:
            raise ApiError("REFERENCE_FIXTURE_NOT_FOUND", "Unknown reference fixture", {"fixtureId": request.fixtureId}, 404)
        fixture = all_fixtures[request.fixtureId]
        label = fixture.id
        user_input = fixture.user_input
        access_log_path = fixture.access_log_path
        fault = fixture.fault
    else:
        if not request.userInput:
            raise ApiError("BAD_REQUEST", "userInput is required for custom-analysis")
        label = "custom-analysis"
        user_input = request.userInput
        access_log_path = Path(request.accessLogPath) if request.accessLogPath else all_fixtures["normal-login-error-spike"].access_log_path
        fault = None

    run_id = make_id("ref", label)
    trace_path = store.reference_trace_path(run_id)
    report_path = store.reference_report_path(run_id)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    logger = TraceLogger(trace_path, run_id=run_id)
    try:
        agent = WebLogAnalysisAgent(logger, fault=fault, use_llm=request.useLlm)
        state = agent.run(user_input, str(access_log_path))
    except Exception as exc:
        logger.close()
        item = store.upsert("reference_runs", {"id": run_id, "mode": request.mode, "status": "failed", "error": {"type": exc.__class__.__name__, "message": str(exc)}})
        raise ApiError("REFERENCE_RUN_FAILED", "Reference agent execution failed", item, 500) from exc
    finally:
        try:
            logger.close()
        except Exception:
            pass

    report_path.write_text(state.finalReport or "", encoding="utf-8")
    item = store.upsert("reference_runs", {
        "id": run_id,
        "mode": request.mode,
        "status": "succeeded",
        "fixtureId": request.fixtureId,
        "userInput": user_input,
        "accessLogPath": str(access_log_path),
        "useLlm": request.useLlm,
        "tracePath": str(trace_path),
        "reportPath": str(report_path),
        "eventCounts": _event_counts(trace_path),
        "timelinePreview": _timeline_preview(trace_path),
    })
    return {"run": item}


def list_reference_runs(store: Optional[ApiStore] = None) -> Dict[str, Any]:
    return {"runs": (store or ApiStore()).list("reference_runs")}


def get_reference_run(run_id: str, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    store = store or ApiStore()
    try:
        run = store.get("reference_runs", run_id)
    except KeyError as exc:
        raise ApiError("REFERENCE_RUN_NOT_FOUND", "Reference run not found", {"runId": run_id}, 404) from exc
    report_path = Path(run.get("reportPath") or "")
    excerpt = report_path.read_text(encoding="utf-8")[:4000] if report_path.exists() else ""
    return {"run": run, "reportExcerpt": excerpt}


def get_reference_trace(run_id: str, *, offset: int = 0, limit: int = 200, event_type: Optional[str] = None, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    run = get_reference_run(run_id, store=store)["run"]
    trace_path = Path(run.get("tracePath") or "")
    if not trace_path.exists():
        raise ApiError("TRACE_NOT_FOUND", "Trace file not found", {"tracePath": str(trace_path)}, 404)
    events = []
    for event in _read_jsonl(trace_path):
        if event_type and event.get("type") != event_type:
            continue
        events.append({"index": event.get("_index"), "type": event.get("type"), "raw": {k: v for k, v in event.items() if k != "_index"}})
    page = events[offset: offset + limit]
    next_offset = offset + limit if offset + limit < len(events) else None
    return {"runId": run_id, "tracePath": str(trace_path), "events": page, "nextOffset": next_offset}


def _summary_from_results(results) -> Dict[str, Any]:
    gates = Counter(result.gate for result in results)
    findings = [finding for result in results for finding in result.findings]
    severities = Counter(finding.severity for finding in findings)
    top = sorted(findings, key=lambda f: (f.severity == "critical", f.severity == "high", f.confidence), reverse=True)[:5]
    return {
        "runCount": len(results),
        "gateCounts": {"pass": gates.get("pass", 0), "warning": gates.get("warning", 0), "block": gates.get("block", 0)},
        "severityCounts": {"low": severities.get("low", 0), "medium": severities.get("medium", 0), "high": severities.get("high", 0), "critical": severities.get("critical", 0)},
        "topFindings": [finding.to_dict() for finding in top],
    }


def create_analysis(request: AnalysisRequest, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    store = store or ApiStore()
    source = request.source
    trace_paths: List[str]
    if source.kind == "reference-run":
        if not source.referenceRunId:
            raise ApiError("BAD_REQUEST", "referenceRunId is required")
        run = get_reference_run(source.referenceRunId, store=store)["run"]
        trace_paths = [str(run.get("tracePath"))]
    else:
        trace_paths = source.tracePaths
    if not trace_paths:
        raise ApiError("BAD_REQUEST", "At least one trace path is required")
    missing = [path for path in trace_paths if not Path(path).exists()]
    if missing:
        raise ApiError("TRACE_NOT_FOUND", "Trace file not found", {"tracePaths": missing}, 404)

    analysis_id = make_id("ana")
    try:
        results = analyze_traces(trace_paths, adapter_name=request.adapter)
    except Exception as exc:
        item = store.upsert("analyses", {"id": analysis_id, "status": "failed", "error": {"type": exc.__class__.__name__, "message": str(exc)}})
        raise ApiError("ANALYSIS_FAILED", "Judge analysis failed", item, 500) from exc

    findings = [finding.to_dict() | {"run_id": result.run.run_id} for result in results for finding in result.findings]
    report = markdown_report(results)
    report_path = store.analysis_report_path(analysis_id)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    data = {
        "id": analysis_id,
        "status": "succeeded",
        "source": {"kind": source.kind, "tracePaths": trace_paths, "referenceRunId": source.referenceRunId},
        "adapter": request.adapter,
        "summary": _summary_from_results(results),
        "results": [result.to_dict() for result in results],
        "findings": findings,
        "reportPath": str(report_path),
    }
    store.analysis_json_path(analysis_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    item = store.upsert("analyses", data)
    return {"analysis": item}


def list_analyses(store: Optional[ApiStore] = None) -> Dict[str, Any]:
    return {"analyses": (store or ApiStore()).list("analyses")}


def get_analysis(analysis_id: str, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    store = store or ApiStore()
    try:
        analysis = store.get("analyses", analysis_id)
    except KeyError as exc:
        raise ApiError("ANALYSIS_NOT_FOUND", "Analysis not found", {"analysisId": analysis_id}, 404) from exc
    report_path = Path(analysis.get("reportPath") or "")
    excerpt = report_path.read_text(encoding="utf-8")[:4000] if report_path.exists() else ""
    return {"analysis": analysis, "reportExcerpt": excerpt}


def _session_response(state: ConversationState, *, mode: str, analysis_id: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": state.session_id,
        "mode": mode,
        "analysisId": analysis_id,
        "loadedTraces": state.loaded_traces,
        "messages": state.messages,
        "focus": state.focus,
        "focusedMetric": state.focused_metric,
        "toolCalls": [call.to_dict() for call in state.tool_calls],
        "evidence": state.evidence,
    }


def create_judge_session(request: JudgeSessionRequest, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    store = store or ApiStore()
    analysis = get_analysis(request.analysisId, store=store)["analysis"]
    state = ConversationState(session_id=request.sessionId)
    state.loaded_traces = list((analysis.get("source") or {}).get("tracePaths") or [])
    state.analysis_results = list(analysis.get("results") or [])
    # Establish initial focus from first finding when possible.
    first = (analysis.get("findings") or [None])[0]
    if first:
        state.set_focus(run_id=first.get("run_id"), finding_id=first.get("id"), metric=first.get("metric"))
    save_conversation_state(store.session_dir(), state)
    item = store.upsert("sessions", {"id": state.session_id, "mode": request.mode, "analysisId": request.analysisId, "sessionPath": str(store.session_dir() / f"{state.session_id}.conversation.json")})
    return {"session": _session_response(state, mode=item["mode"], analysis_id=item.get("analysisId"))}


def list_judge_sessions(store: Optional[ApiStore] = None) -> Dict[str, Any]:
    return {"sessions": (store or ApiStore()).list("sessions")}


def get_judge_session(session_id: str, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    store = store or ApiStore()
    try:
        meta = store.get("sessions", session_id)
    except KeyError as exc:
        raise ApiError("SESSION_NOT_FOUND", "Judge session not found", {"sessionId": session_id}, 404) from exc
    state = load_conversation_state(store.session_dir(), session_id)
    return {"session": _session_response(state, mode=meta.get("mode", "deterministic-v2"), analysis_id=meta.get("analysisId"))}


def send_judge_message(session_id: str, request: JudgeMessageRequest, store: Optional[ApiStore] = None) -> Dict[str, Any]:
    store = store or ApiStore()
    try:
        meta = store.get("sessions", session_id)
    except KeyError as exc:
        raise ApiError("SESSION_NOT_FOUND", "Judge session not found", {"sessionId": session_id}, 404) from exc
    if not request.content.strip():
        raise ApiError("BAD_REQUEST", "content is required")
    state = load_conversation_state(store.session_dir(), session_id)
    mode = meta.get("mode", "deterministic-v2")
    if mode == "hybrid":
        llm = create_llm_client(**(meta.get("llm") or {}))
        agent = HybridConversationAgent(state, llm=llm)
    elif mode == "graph":
        llm = create_llm_client(**(meta.get("llm") or {}))
        agent = GraphConversationAgent(state, llm=llm)
    else:
        agent = ToolBasedConversationAgent(state)
    response = agent.handle_user_turn(request.content)
    save_conversation_state(store.session_dir(), state)
    store.upsert("sessions", dict(meta))
    message = {
        "id": make_id("msg"),
        "role": "assistant",
        "content": response,
        "focusedFindingId": state.focus.get("finding_id"),
        "focusedMetric": state.focused_metric,
        "toolCalls": [call.to_dict() for call in state.tool_calls[-3:]],
    }
    return {"message": message, "session": _session_response(state, mode=mode, analysis_id=meta.get("analysisId"))}
