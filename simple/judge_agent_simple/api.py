from __future__ import annotations

from typing import Any, Dict, Optional

from .api_models import (
    ApiError,
    analysis_request,
    judge_message_request,
    judge_session_request,
    reference_run_request,
)
from .api_services import (
    config_snapshot,
    create_analysis,
    create_judge_session,
    get_analysis,
    get_judge_session,
    get_reference_run,
    get_reference_trace,
    health,
    list_analyses,
    list_judge_sessions,
    list_reference_fixtures,
    list_reference_runs,
    metric_list,
    run_reference_agent,
    send_judge_message,
)

try:  # Optional dependency; installed with `pip install -e '.[api]'`.
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
except Exception:  # pragma: no cover - exercised only when optional deps missing.
    FastAPI = None  # type: ignore
    Query = None  # type: ignore
    CORSMiddleware = None  # type: ignore
    JSONResponse = None  # type: ignore


def _api_error_response(exc: ApiError):
    if JSONResponse is None:
        raise exc
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install with: pip install -e '.[api]'")

    app = FastAPI(title="Judge Agent Frontend API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def handle_api_error(_request, exc: ApiError):
        return _api_error_response(exc)

    @app.get("/api/health")
    def api_health():
        return health()

    @app.get("/api/config")
    def api_config():
        return config_snapshot()

    @app.get("/api/metrics")
    def api_metrics():
        return metric_list()

    @app.get("/api/reference/fixtures")
    def api_reference_fixtures():
        return list_reference_fixtures()

    @app.post("/api/reference/runs")
    def api_reference_runs(payload: Dict[str, Any]):
        return run_reference_agent(reference_run_request(payload))

    @app.get("/api/reference/runs")
    def api_reference_runs_list():
        return list_reference_runs()

    @app.get("/api/reference/runs/{run_id}")
    def api_reference_run(run_id: str):
        return get_reference_run(run_id)

    @app.get("/api/reference/runs/{run_id}/trace")
    def api_reference_trace(run_id: str, offset: int = 0, limit: int = 200, type: Optional[str] = None):
        return get_reference_trace(run_id, offset=offset, limit=limit, event_type=type)

    @app.post("/api/analyses")
    def api_create_analysis(payload: Dict[str, Any]):
        return create_analysis(analysis_request(payload))

    @app.get("/api/analyses")
    def api_list_analyses():
        return list_analyses()

    @app.get("/api/analyses/{analysis_id}")
    def api_get_analysis(analysis_id: str):
        return get_analysis(analysis_id)

    @app.post("/api/judge/sessions")
    def api_create_judge_session(payload: Dict[str, Any]):
        return create_judge_session(judge_session_request(payload))

    @app.get("/api/judge/sessions")
    def api_list_judge_sessions():
        return list_judge_sessions()

    @app.get("/api/judge/sessions/{session_id}")
    def api_get_judge_session(session_id: str):
        return get_judge_session(session_id)

    @app.post("/api/judge/sessions/{session_id}/messages")
    def api_send_judge_message(session_id: str, payload: Dict[str, Any]):
        return send_judge_message(session_id, judge_message_request(payload))

    return app


app = create_app() if FastAPI is not None else None
