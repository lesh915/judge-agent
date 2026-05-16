from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.session import JudgeSessionState, safe_session_id


@dataclass
class ToolCallRecord:
    tool: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationState:
    session_id: str
    schema_version: int = 2
    messages: List[Dict[str, Any]] = field(default_factory=list)
    loaded_traces: List[str] = field(default_factory=list)
    analysis_results: List[Dict[str, Any]] = field(default_factory=list)
    focus: Dict[str, Any] = field(default_factory=dict)
    focused_metric: Optional[str] = None
    metric_history: List[str] = field(default_factory=list)
    severity_filter: Optional[str] = None
    pending_question: Optional[str] = None
    plan: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    final_response: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content, "timestamp": time.time()})
        self.updated_at = time.time()

    def record_tool(self, tool: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> None:
        self.tool_calls.append(ToolCallRecord(tool=tool, arguments=arguments, result=result))
        metric = result.get("metric") or result.get("focused_metric")
        if metric:
            self.focused_metric = str(metric)
            if str(metric) not in self.metric_history:
                self.metric_history.append(str(metric))
        self.updated_at = time.time()

    def set_focus(self, *, run_id: Optional[str] = None, finding_id: Optional[str] = None, metric: Optional[str] = None) -> None:
        if run_id is not None:
            self.focus["run_id"] = run_id
        if finding_id is not None:
            self.focus["finding_id"] = finding_id
        if metric is not None:
            self.focus["metric"] = metric
            self.focused_metric = metric
            if metric not in self.metric_history:
                self.metric_history.append(metric)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "messages": self.messages[-80:],
            "loaded_traces": self.loaded_traces,
            "analysis_results": self.analysis_results,
            "focus": self.focus,
            "focused_metric": self.focused_metric,
            "metric_history": self.metric_history[-40:],
            "severity_filter": self.severity_filter,
            "pending_question": self.pending_question,
            "plan": self.plan,
            "tool_calls": [call.to_dict() for call in self.tool_calls[-80:]],
            "evidence": self.evidence[-80:],
            "final_response": self.final_response,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        if int(data.get("schema_version") or 1) < 2 and "turns" in data:
            return cls.from_judge_session(JudgeSessionState.from_dict(data))
        state = cls(
            session_id=data["session_id"],
            schema_version=int(data.get("schema_version") or 2),
            messages=data.get("messages") or [],
            loaded_traces=data.get("loaded_traces") or [],
            analysis_results=data.get("analysis_results") or [],
            focus=data.get("focus") or {},
            focused_metric=data.get("focused_metric"),
            metric_history=data.get("metric_history") or [],
            severity_filter=data.get("severity_filter"),
            pending_question=data.get("pending_question"),
            plan=data.get("plan") or [],
            evidence=data.get("evidence") or [],
            final_response=data.get("final_response"),
            created_at=float(data.get("created_at") or time.time()),
            updated_at=float(data.get("updated_at") or time.time()),
        )
        state.tool_calls = [ToolCallRecord(**call) for call in data.get("tool_calls", [])]
        return state

    @classmethod
    def from_judge_session(cls, session: JudgeSessionState) -> "ConversationState":
        state = cls(
            session_id=session.session_id,
            messages=[turn.to_dict() for turn in session.turns],
            analysis_results=session.analysis_results,
            focus=session.focus,
            focused_metric=session.focus.get("metric"),
            metric_history=[session.focus.get("metric")] if session.focus.get("metric") else [],
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        return state


def conversation_session_path(session_dir: Path, session_id: str) -> Path:
    return session_dir / f"{safe_session_id(session_id)}.conversation.json"


def load_conversation_state(session_dir: Path, session_id: str) -> ConversationState:
    path = conversation_session_path(session_dir, session_id)
    return ConversationState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_conversation_state(session_dir: Path, state: ConversationState) -> Path:
    session_dir.mkdir(parents=True, exist_ok=True)
    path = conversation_session_path(session_dir, state.session_id)
    path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
