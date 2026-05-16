from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .fixtures import TRACE_DIR

SESSION_DIR = TRACE_DIR.parent / "sessions"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_session_id() -> str:
    return f"chat-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"


@dataclass
class ChatSessionState:
    """Persisted state for an interactive web log analysis conversation.

    The full ReAct analysis trace remains in jsonl files. This state stores only
    bounded conversation context and compact analysis summaries so follow-up
    turns can answer from prior context without replaying raw logs.
    """

    session_id: str
    access_log_path: str
    log_format: str = "nginx_combined"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    turns: List[Dict[str, Any]] = field(default_factory=list)
    current_focus: Dict[str, Any] = field(default_factory=dict)
    last_analysis: Optional[Dict[str, Any]] = None
    summaries: List[str] = field(default_factory=list)

    def add_turn(self, role: str, content: str, **metadata: Any) -> None:
        self.turns.append({"role": role, "content": content, "ts": utc_now_iso(), **metadata})
        self.updated_at = utc_now_iso()

    def compact_recent_turns(self, limit: int = 8) -> List[Dict[str, Any]]:
        return self.turns[-limit:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "access_log_path": self.access_log_path,
            "log_format": self.log_format,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turns": self.turns,
            "current_focus": self.current_focus,
            "last_analysis": self.last_analysis,
            "summaries": self.summaries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatSessionState":
        return cls(
            session_id=data["session_id"],
            access_log_path=data["access_log_path"],
            log_format=data.get("log_format", "nginx_combined"),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
            turns=list(data.get("turns", [])),
            current_focus=dict(data.get("current_focus", {})),
            last_analysis=data.get("last_analysis"),
            summaries=list(data.get("summaries", [])),
        )


def session_path(session_id: str, session_dir: Path = SESSION_DIR) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in session_id)
    return session_dir / f"{safe}.json"


def load_session(session_id: str, session_dir: Path = SESSION_DIR) -> ChatSessionState:
    path = session_path(session_id, session_dir)
    return ChatSessionState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_session(session: ChatSessionState, session_dir: Path = SESSION_DIR) -> Path:
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_path(session.session_id, session_dir)
    path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_sessions(session_dir: Path = SESSION_DIR) -> List[Dict[str, Any]]:
    if not session_dir.exists():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(session_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append({
                "session_id": data.get("session_id", path.stem),
                "updated_at": data.get("updated_at"),
                "turn_count": len(data.get("turns", [])),
                "access_log_path": data.get("access_log_path"),
                "path": str(path),
            })
        except Exception:
            out.append({"session_id": path.stem, "path": str(path), "error": "failed_to_read"})
    return out
