from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .schema import SimpleAgentRun, SimpleEvent


class ReferenceAgentJsonlAdapter:
    """Normalize reference_agent.weblog_agent TraceLogger JSONL events."""

    name = "reference-weblog-jsonl"

    def load(self, path: str | Path) -> SimpleAgentRun:
        trace_path = Path(path)
        raw_events = self._read_jsonl(trace_path)
        if not raw_events:
            raise ValueError(f"empty trace: {trace_path}")
        run_id = str(raw_events[0].get("run_id") or trace_path.stem)
        run = SimpleAgentRun(run_id=run_id, raw_events=raw_events, artifacts={"tracePath": str(trace_path)})
        for raw in raw_events:
            self._apply_raw_event(run, raw)
            event = self._normalize_event(raw)
            if event:
                run.events.append(event)
        return run

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_no}: {exc}") from exc
        return events

    def _apply_raw_event(self, run: SimpleAgentRun, raw: Dict[str, Any]) -> None:
        event_type = raw.get("type")
        if event_type == "run_start":
            run.agent_name = raw.get("agent_name")
            run.agent_version = raw.get("agent_version")
            run.framework = raw.get("framework") or run.framework
            run.architecture = raw.get("architecture")
            run.graph_version = raw.get("graph_version")
            run.user_input = raw.get("user_input")
            run.metadata.update({
                "llm_model": raw.get("llm_model"),
                "llm_enabled": raw.get("llm_enabled"),
            })
        elif event_type == "chat_session_start":
            run.framework = "reference-weblog"
            run.architecture = "chat"
            run.metadata.update({
                "session_id": raw.get("session_id"),
                "access_log_path": raw.get("access_log_path"),
                "llm_model": raw.get("llm_model"),
                "llm_enabled": raw.get("llm_enabled"),
            })
        elif event_type == "chat_turn_start" and not run.user_input:
            run.user_input = raw.get("user_input")
        elif event_type == "instruction_snapshot":
            run.instructions = {
                "system": raw.get("system"),
                "reactProtocol": raw.get("react_protocol"),
                "toolPolicy": raw.get("tool_policy"),
                "outputContract": raw.get("output_contract"),
            }
        elif event_type == "agent_components":
            run.components = {
                "llm": raw.get("llm"),
                "prompt": raw.get("prompt"),
                "tools": raw.get("tools"),
                "mcpServers": raw.get("mcp_servers"),
                "mcpTools": raw.get("mcp_tools"),
                "rag": raw.get("rag"),
            }
        elif event_type == "validation_result":
            run.validation_results.append(raw)
        elif event_type == "final_output":
            run.final_output = raw.get("content")

    def _normalize_event(self, raw: Dict[str, Any]) -> SimpleEvent | None:
        event_type = raw.get("type")
        event_id = str(raw.get("event_id") or f"{event_type}-{raw.get('timestamp', '')}")
        ts = raw.get("timestamp")
        if event_type in {"llm_start", "llm_end", "llm_error", "llm_skipped"}:
            return SimpleEvent(event_id, "llm_call", raw.get("name"), ts, raw.get("messages"), raw.get("output"), {k: v for k, v in raw.items() if k not in {"messages", "output"}})
        if event_type in {"tool_start", "tool_end", "tool_error"}:
            return SimpleEvent(event_id, "tool_call" if event_type == "tool_start" else "tool_result", raw.get("tool"), ts, raw.get("arguments"), raw.get("output") or raw.get("error"), raw)
        if event_type in {"mcp_start", "mcp_end", "mcp_error"}:
            return SimpleEvent(event_id, "tool_call" if event_type == "mcp_start" else "tool_result", raw.get("tool") or raw.get("method"), ts, raw.get("arguments"), raw.get("output") or raw.get("error"), raw)
        if event_type in {"node_start", "node_end"}:
            return SimpleEvent(event_id, "graph_node", raw.get("node"), ts, raw.get("state_before"), raw.get("state_after"), raw)
        if event_type == "edge_selected":
            return SimpleEvent(event_id, "graph_edge", f"{raw.get('from')}->{raw.get('to')}", ts, None, None, raw)
        if event_type in {"react_step", "observation"}:
            return SimpleEvent(event_id, "react", raw.get("action"), ts, raw.get("action_input"), raw.get("observation"), raw)
        if event_type == "validation_result":
            return SimpleEvent(event_id, "validation", "validation_result", ts, raw.get("checks"), {"passed": raw.get("passed"), "issues": raw.get("issues")}, raw)
        if event_type and event_type.startswith("chat_"):
            return SimpleEvent(event_id, "chat_turn", event_type, ts, raw.get("user_input"), raw.get("response"), raw)
        if event_type == "final_output":
            return SimpleEvent(event_id, "final_output", "final_output", ts, None, raw.get("content"), raw)
        if event_type in {"run_start", "run_end", "instruction_snapshot", "agent_components"}:
            return SimpleEvent(event_id, event_type, event_type, ts, None, None, raw)
        return None
