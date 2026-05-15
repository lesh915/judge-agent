from __future__ import annotations

import json
from typing import Any, Dict, List


HYBRID_SYSTEM_PROMPT = """You are a conversational Judge Agent for LangChain/LangGraph agent drift analysis.

Rules:
- Answer only from provided tool results, metric metadata, and evidence.
- Do not invent findings, traces, metrics, or code locations.
- If evidence is insufficient, say what is missing.
- Keep Korean answers concise and technical.
- Include metric names, severity, and concrete evidence when relevant.
- Separate measured evidence from interpretation/recommendation.
"""


def build_hybrid_messages(user_input: str, deterministic_answer: str, tool_results: List[Dict[str, Any]], state_summary: Dict[str, Any]) -> List[Dict[str, str]]:
    payload = {
        "user_input": user_input,
        "deterministic_answer": deterministic_answer,
        "tool_results": tool_results,
        "state_summary": state_summary,
    }
    return [
        {"role": "system", "content": HYBRID_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2, default=str)},
    ]


def compact_state_summary(state) -> Dict[str, Any]:
    return {
        "session_id": state.session_id,
        "loaded_trace_count": len(state.loaded_traces),
        "run_count": len(state.analysis_results),
        "focus": state.focus,
        "focused_metric": state.focused_metric,
        "metric_history": state.metric_history[-8:],
        "tool_call_count": len(state.tool_calls),
    }
