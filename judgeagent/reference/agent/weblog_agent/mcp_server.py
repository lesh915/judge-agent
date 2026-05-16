from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

SERVICE_CONTEXTS: Dict[str, Dict[str, Any]] = {
    "/api/login": {
        "service": "identity-api",
        "owner": "identity-platform",
        "recentDeployments": ["identity-api@2026.05.13-03", "session-store@2026.05.12-21"],
        "dependencies": ["auth-provider", "session-store", "user-db"],
        "slo": {"availability": "99.9%", "p95LatencyMs": 800},
        "runbookRefs": ["runbook:/api/login"],
    },
    "/api/payment": {
        "service": "payment-api",
        "owner": "payments-platform",
        "recentDeployments": ["payment-api@2026.05.13-01"],
        "dependencies": ["psp-gateway", "fraud-service"],
        "slo": {"availability": "99.95%", "p95LatencyMs": 900},
        "runbookRefs": ["runbook:/api/payment"],
    },
}

TOOLS = [
    {
        "name": "get_service_context",
        "description": "Return service ownership, deployment, dependency and SLO metadata for an API path.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "API path such as /api/login"}},
            "required": ["path"],
        },
    }
]


def get_service_context(path: Optional[str]) -> Dict[str, Any]:
    return SERVICE_CONTEXTS.get(path or "", {
        "service": "unknown-service",
        "owner": "unknown",
        "recentDeployments": [],
        "dependencies": [],
        "slo": {},
        "runbookRefs": [],
        "warning": f"No service context found for path={path!r}",
    })


def _result(request_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if method == "initialize":
        return _result(request_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "weblog-service-context-mcp", "version": "0.1.0"},
            "capabilities": {"tools": {"listChanged": False}},
        })
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != "get_service_context":
            return _error(request_id, -32601, f"Unknown tool: {name}")
        data = get_service_context(arguments.get("path"))
        return _result(request_id, {
            "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
            "structuredContent": data,
            "isError": False,
        })
    return _error(request_id, -32601, f"Unknown method: {method}")


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


def main() -> int:
    _configure_stdio()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle(request)
        except Exception as exc:
            response = _error(None, -32700, f"Invalid request: {exc}")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
