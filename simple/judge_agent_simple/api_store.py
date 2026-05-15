from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .core.session import safe_session_id

DEFAULT_API_ROOT = Path("artifacts/frontend-api")


def now_ts() -> float:
    return time.time()


def make_id(prefix: str, label: Optional[str] = None) -> str:
    stamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    suffix = f"_{safe_session_id(label)}" if label else ""
    return f"{prefix}_{stamp}{suffix}"


class ApiStore:
    """Small file-backed registry for frontend API resources.

    This is intentionally simple and replaceable. A future DB-backed store should
    preserve the public methods and resource shapes used by api_services.py.
    """

    def __init__(self, root: Union[Path, str] = DEFAULT_API_ROOT):
        self.root = Path(root)
        self.reference_root = self.root / "reference-runs"
        self.analysis_root = self.root / "analyses"
        self.session_root = self.root / "judge-sessions"

    def ensure(self) -> None:
        for path in [
            self.reference_root / "traces",
            self.reference_root / "reports",
            self.analysis_root / "reports",
            self.session_root,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def _registry_path(self, kind: str) -> Path:
        if kind == "reference_runs":
            return self.reference_root / "registry.json"
        if kind == "analyses":
            return self.analysis_root / "registry.json"
        if kind == "sessions":
            return self.session_root / "registry.json"
        raise KeyError(kind)

    def _read_registry(self, kind: str) -> Dict[str, Dict[str, Any]]:
        path = self._registry_path(kind)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_registry(self, kind: str, data: Dict[str, Dict[str, Any]]) -> None:
        self.ensure()
        path = self._registry_path(kind)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, kind: str, item: Dict[str, Any]) -> Dict[str, Any]:
        registry = self._read_registry(kind)
        item = dict(item)
        item.setdefault("createdAt", now_ts())
        item["updatedAt"] = now_ts()
        registry[item["id"]] = item
        self._write_registry(kind, registry)
        return item

    def get(self, kind: str, item_id: str) -> Dict[str, Any]:
        registry = self._read_registry(kind)
        if item_id not in registry:
            raise KeyError(item_id)
        return registry[item_id]

    def list(self, kind: str) -> List[Dict[str, Any]]:
        registry = self._read_registry(kind)
        return sorted(registry.values(), key=lambda item: item.get("createdAt", 0), reverse=True)

    def reference_trace_path(self, run_id: str) -> Path:
        return self.reference_root / "traces" / f"{safe_session_id(run_id)}.jsonl"

    def reference_report_path(self, run_id: str) -> Path:
        return self.reference_root / "reports" / f"{safe_session_id(run_id)}.md"

    def analysis_json_path(self, analysis_id: str) -> Path:
        return self.analysis_root / f"{safe_session_id(analysis_id)}.json"

    def analysis_report_path(self, analysis_id: str) -> Path:
        return self.analysis_root / "reports" / f"{safe_session_id(analysis_id)}.md"

    def session_dir(self) -> Path:
        self.ensure()
        return self.session_root
