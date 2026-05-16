from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ApiError(Exception):
    code: str
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)
    status_code: int = 400

    def to_dict(self) -> Dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "detail": self.detail}}


@dataclass
class ReferenceRunRequest:
    mode: str = "fixture"
    fixtureId: Optional[str] = None
    userInput: Optional[str] = None
    accessLogPath: Optional[str] = None
    useLlm: bool = True


@dataclass
class AnalysisSource:
    kind: str
    tracePaths: List[str] = field(default_factory=list)
    referenceRunId: Optional[str] = None


@dataclass
class AnalysisRequest:
    source: AnalysisSource
    adapter: str = "reference-weblog-jsonl"


@dataclass
class JudgeSessionRequest:
    analysisId: str
    sessionId: str = "default"
    mode: str = "deterministic-v2"
    llm: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeMessageRequest:
    content: str
    context: Dict[str, Any] = field(default_factory=dict)


def reference_run_request(data: Dict[str, Any]) -> ReferenceRunRequest:
    return ReferenceRunRequest(
        mode=str(data.get("mode") or "fixture"),
        fixtureId=data.get("fixtureId") or data.get("fixture_id"),
        userInput=data.get("userInput") or data.get("user_input"),
        accessLogPath=data.get("accessLogPath") or data.get("access_log_path"),
        useLlm=bool(data.get("useLlm", data.get("use_llm", True))),
    )


def analysis_request(data: Dict[str, Any]) -> AnalysisRequest:
    source = data.get("source") or {}
    return AnalysisRequest(
        source=AnalysisSource(
            kind=str(source.get("kind") or "trace-paths"),
            tracePaths=[str(path) for path in source.get("tracePaths") or source.get("trace_paths") or []],
            referenceRunId=source.get("referenceRunId") or source.get("reference_run_id"),
        ),
        adapter=str(data.get("adapter") or "reference-weblog-jsonl"),
    )


def judge_session_request(data: Dict[str, Any]) -> JudgeSessionRequest:
    return JudgeSessionRequest(
        analysisId=str(data.get("analysisId") or data.get("analysis_id")),
        sessionId=str(data.get("sessionId") or data.get("session_id") or "default"),
        mode=str(data.get("mode") or "deterministic-v2"),
        llm=data.get("llm") or {},
    )


def judge_message_request(data: Dict[str, Any]) -> JudgeMessageRequest:
    return JudgeMessageRequest(content=str(data.get("content") or ""), context=data.get("context") or {})
