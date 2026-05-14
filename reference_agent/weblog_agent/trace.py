from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Union

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)=([^&\s]+)"),
]


def redact(value: Any) -> Any:
    if isinstance(value, str):
        out = value
        for pattern in SECRET_PATTERNS:
            out = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", out)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value


class TraceLogger:
    def __init__(self, path: Union[str, Path], run_id: Optional[str] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
        self._fh = self.path.open("w", encoding="utf-8")

    def close(self) -> None:
        self._fh.close()

    def emit(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        event = {
            "type": event_type,
            "run_id": self.run_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **payload,
        }
        event = redact(event)
        self._fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        self._fh.flush()
        return event

    def node_start(self, node: str, state_before: Dict[str, Any]) -> str:
        event_id = f"node-{node}-{uuid.uuid4().hex[:6]}"
        self.emit("node_start", event_id=event_id, node=node, state_before=state_before)
        return event_id

    def node_end(self, event_id: str, node: str, state_after: Dict[str, Any]) -> None:
        self.emit("node_end", event_id=event_id, node=node, state_after=state_after)

    def tool_start(self, tool: str, arguments: Dict[str, Any], source_event_ids=None) -> str:
        event_id = f"tool-{tool}-{uuid.uuid4().hex[:6]}"
        self.emit("tool_start", event_id=event_id, tool=tool, arguments=arguments, source_event_ids=source_event_ids or [])
        return event_id

    def tool_end(self, event_id: str, tool: str, output: Dict[str, Any]) -> None:
        self.emit("tool_end", event_id=event_id, tool=tool, output=output)

    def tool_error(self, event_id: str, tool: str, error: Dict[str, Any]) -> None:
        self.emit("tool_error", event_id=event_id, tool=tool, error=error)
