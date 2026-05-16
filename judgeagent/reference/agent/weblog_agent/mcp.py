from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional


class MCPClientError(RuntimeError):
    pass


class StdioMCPClient:
    """Small functional MCP stdio client for the reference agent.

    It starts the local MCP server (`python -m reference_agent.weblog_agent.mcp_server`)
    and talks to it with JSON-RPC messages compatible with the MCP tool methods
    used by this reference agent: initialize, tools/list, and tools/call.
    """

    def __init__(self, command: Optional[List[str]] = None):
        self.command = command or [sys.executable, "-m", "reference_agent.weblog_agent.mcp_server"]
        self._proc: Optional[subprocess.Popen[str]] = None
        self._next_id = 1
        self._lock = threading.Lock()
        self.server_info: Dict[str, Any] = {}

    @property
    def server_name(self) -> str:
        return self.server_info.get("serverInfo", {}).get("name", "weblog-service-context-mcp")

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        popen_kwargs: Dict[str, Any] = {}
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
            **popen_kwargs,
        )
        self.server_info = self._request("initialize", {"clientInfo": {"name": "weblog-react-agent", "version": "0.3.0"}})
        self._notify("notifications/initialized", {})

    def list_tools(self) -> Dict[str, Any]:
        self.start()
        return self._request("tools/list", {})

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.start()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise MCPClientError(f"MCP tool returned error: {result}")
        if "structuredContent" in result:
            return result["structuredContent"]
        content = result.get("content") or []
        if content and content[0].get("type") == "text":
            return json.loads(content[0].get("text") or "{}")
        return result

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if not proc:
            return
        if proc.stdin:
            try:
                proc.stdin.close()
            except Exception:
                pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        for stream in (proc.stdout, proc.stderr):
            if stream:
                try:
                    stream.close()
                except Exception:
                    pass

    def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if not self._proc or not self._proc.stdin or not self._proc.stdout:
                raise MCPClientError("MCP process is not running")
            request_id = self._next_id
            self._next_id += 1
            message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
            self._proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                stderr = self._proc.stderr.read() if self._proc.stderr else ""
                raise MCPClientError(f"MCP server closed without response. stderr={stderr}")
            response = json.loads(line)
            if response.get("id") != request_id:
                raise MCPClientError(f"MCP response id mismatch: expected={request_id} response={response}")
            if "error" in response:
                raise MCPClientError(f"MCP error: {response['error']}")
            return response.get("result", {})

    def _notify(self, method: str, params: Dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise MCPClientError("MCP process is not running")
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
