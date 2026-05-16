from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class JudgeTurn:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JudgeSessionState:
    session_id: str
    turns: List[JudgeTurn] = field(default_factory=list)
    analysis_results: List[Dict[str, Any]] = field(default_factory=list)
    focus: Dict[str, Any] = field(default_factory=dict)
    last_intent: Optional[str] = None
    summary: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(JudgeTurn(role=role, content=content))
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns": [turn.to_dict() for turn in self.turns[-40:]],
            "analysis_results": self.analysis_results,
            "focus": self.focus,
            "last_intent": self.last_intent,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JudgeSessionState":
        state = cls(
            session_id=data["session_id"],
            analysis_results=data.get("analysis_results") or [],
            focus=data.get("focus") or {},
            last_intent=data.get("last_intent"),
            summary=data.get("summary"),
            created_at=float(data.get("created_at") or time.time()),
            updated_at=float(data.get("updated_at") or time.time()),
        )
        state.turns = [JudgeTurn(**turn) for turn in data.get("turns", [])]
        return state


def safe_session_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return safe or "default"


def session_path(session_dir: Path, session_id: str) -> Path:
    return session_dir / f"{safe_session_id(session_id)}.json"


def load_session(session_dir: Path, session_id: str) -> JudgeSessionState:
    path = session_path(session_dir, session_id)
    return JudgeSessionState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_session(session_dir: Path, state: JudgeSessionState) -> Path:
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_path(session_dir, state.session_id)
    path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
