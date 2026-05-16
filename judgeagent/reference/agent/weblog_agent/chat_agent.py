from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .fixtures import REPORT_DIR, TRACE_DIR
from .graph import WebLogAnalysisAgent, parse_request_text
from .llm import LLMClient
from .session import ChatSessionState, save_session
from .trace import TraceLogger

CHAT_SYSTEM_PROMPT = """You are an interactive web log analysis agent.
Answer follow-up questions using the provided session context. Do not invent metrics,
causes, log lines, owners, deployments, or runbook facts. If the user asks for a new
endpoint or a new analysis, request or run a new analysis instead of pretending prior
results apply. Keep answers concise and operational."""

ANALYSIS_KEYWORDS = (
    "analyze", "analyse", "분석", "에러율", "error rate", "5xx", "latency", "지연", "로그", "log", "compare", "비교"
)
FOLLOWUP_KEYWORDS = (
    "방금", "이전", "위", "그", "원인", "cause", "why", "왜", "추천", "조치", "action", "요약", "summary", "owner", "담당"
)


def summarize_analysis_state(state) -> Dict[str, Any]:
    report = state.finalReport or ""
    return {
        "request": state.request,
        "logSource": state.logSource,
        "metrics": state.metrics,
        "anomalies": state.anomalies,
        "evidence": state.evidence,
        "ragContext": state.ragContext[:3],
        "mcpContext": state.mcpContext,
        "validation": state.validation,
        "errors": state.errors,
        "report_excerpt": report[:4000],
    }


def render_analysis_summary(summary: Dict[str, Any]) -> str:
    request = summary.get("request", {})
    metrics = summary.get("metrics", {})
    anomalies = summary.get("anomalies", [])
    target = request.get("targetPath") or "requested target"
    lines = [
        f"분석 완료: `{target}`",
        "",
        "핵심 지표:",
        f"- request_count: {metrics.get('request_count', 0)}",
        f"- error_count: {metrics.get('error_count', 0)}",
        f"- 5xx_count: {metrics.get('5xx_count', 0)}",
        f"- error_rate: {float(metrics.get('error_rate', 0.0)):.2%}",
        f"- p95_latency_ms: {metrics.get('p95_latency_ms', 0)}",
        "",
        "이상 징후:",
    ]
    if anomalies:
        for item in anomalies[:5]:
            lines.append(f"- {item.get('type')} ({item.get('severity')}): {item.get('reason')}")
    else:
        lines.append("- threshold 기준 이상 징후는 감지되지 않았습니다.")
    return "\n".join(lines)


def deterministic_followup_response(context: Dict[str, Any], user_input: str) -> str:
    last = context.get("last_analysis") or {}
    metrics = last.get("metrics") or {}
    anomalies = last.get("anomalies") or []
    mcp = last.get("mcpContext") or {}
    rag = last.get("ragContext") or []
    target = (last.get("request") or {}).get("targetPath") or "이전 분석 대상"

    lower = user_input.lower()
    if "owner" in lower or "담당" in user_input:
        return f"이전 분석 기준 담당자는 `{mcp.get('owner', 'unknown')}`입니다. 서비스는 `{mcp.get('service', 'unknown')}`로 기록되어 있어요."
    if "요약" in user_input or "summary" in lower:
        return render_analysis_summary(last)
    if "원인" in user_input or "cause" in lower or "why" in lower or "왜" in user_input:
        if anomalies:
            reason = anomalies[0].get("reason", "이상 징후가 감지되었습니다.")
            runbook = rag[0].get("content", "") if rag else ""
            extra = f" runbook 기준으로는 {runbook.splitlines()[0]}" if runbook else ""
            return f"가능성이 가장 큰 원인은 `{target}`의 오류율/지연 이상입니다. 근거: {reason}.{extra} 단, 원인 확정은 서비스 로그와 최근 배포 확인이 필요합니다."
        return f"`{target}`에서는 threshold 기준 이상 징후가 없어 명확한 원인은 특정하기 어렵습니다. error_rate={float(metrics.get('error_rate', 0.0)):.2%}입니다."
    if "조치" in user_input or "action" in lower or "추천" in user_input:
        return "권장 조치: 최근 배포 확인, 의존 서비스 상태 점검, 대표 5xx 로그와 애플리케이션 로그 매칭, SLO/error budget 영향 확인 순서로 보시면 됩니다."
    return render_analysis_summary(last)


class ChatAgent:
    """Interactive conversation wrapper around the single-run ReAct agent."""

    def __init__(self, session: ChatSessionState, trace_logger: TraceLogger, use_llm: bool = True, llm: Optional[LLMClient] = None, session_dir: Optional[Path] = None):
        self.session = session
        self.trace = trace_logger
        self.use_llm = use_llm
        self.llm = llm or LLMClient()
        self.session_dir = session_dir

    def start(self) -> None:
        self.trace.emit(
            "chat_session_start",
            session_id=self.session.session_id,
            access_log_path=self.session.access_log_path,
            log_format=self.session.log_format,
            turn_count=len(self.session.turns),
            llm_enabled=bool(self.use_llm and self.llm.enabled),
            llm_model=self.llm.config.model,
            llm_config=self.llm.config.sanitized(),
        )

    def end(self) -> None:
        self.trace.emit("chat_session_end", session_id=self.session.session_id, turn_count=len(self.session.turns))

    def handle_user_turn(self, user_input: str, *, report_dir: Path = REPORT_DIR, trace_dir: Path = TRACE_DIR) -> str:
        turn_no = len([t for t in self.session.turns if t.get("role") == "user"]) + 1
        self.trace.emit("chat_turn_start", session_id=self.session.session_id, turn=turn_no, user_input=user_input)
        self.session.add_turn("user", user_input)

        intent = self.classify_intent(user_input)
        self.trace.emit("chat_intent_classified", session_id=self.session.session_id, turn=turn_no, intent=intent)

        if intent == "new_analysis":
            response = self._run_analysis_turn(user_input, turn_no, report_dir=report_dir, trace_dir=trace_dir)
        elif intent == "clarification":
            response = "분석할 endpoint나 조건을 조금만 더 알려주세요. 예: `/api/login 5xx 에러율 분석해줘`"
        else:
            response = self._answer_followup(user_input)

        self.session.add_turn("assistant", response, intent=intent)
        save_session(self.session, session_dir=self.session_dir or Path(TRACE_DIR.parent / "sessions"))
        self.trace.emit("chat_response_generated", session_id=self.session.session_id, turn=turn_no, intent=intent, response=response)
        self.trace.emit("chat_turn_end", session_id=self.session.session_id, turn=turn_no)
        return response

    def classify_intent(self, user_input: str) -> str:
        parsed = parse_request_text(user_input)
        has_path = bool(parsed.get("targetPath"))
        lower = user_input.lower()
        asks_analysis = any(k in lower or k in user_input for k in ANALYSIS_KEYWORDS)
        asks_followup = any(k in lower or k in user_input for k in FOLLOWUP_KEYWORDS)
        if has_path and asks_analysis:
            return "new_analysis"
        if self.session.last_analysis and asks_followup:
            return "followup"
        if has_path:
            return "new_analysis"
        if self.session.last_analysis:
            return "followup"
        return "clarification"

    def build_chat_context(self, user_input: str) -> Dict[str, Any]:
        context = {
            "session_id": self.session.session_id,
            "access_log_path": self.session.access_log_path,
            "current_focus": self.session.current_focus,
            "recent_turns": self.session.compact_recent_turns(limit=8),
            "summaries": self.session.summaries[-3:],
            "last_analysis": self.session.last_analysis,
            "user_input": user_input,
        }
        self.trace.emit(
            "chat_context_built",
            session_id=self.session.session_id,
            recent_turn_count=len(context["recent_turns"]),
            has_last_analysis=bool(self.session.last_analysis),
            summary_count=len(context["summaries"]),
        )
        return context

    def _run_analysis_turn(self, user_input: str, turn_no: int, *, report_dir: Path, trace_dir: Path) -> str:
        trace_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)
        child_trace_path = trace_dir / f"{self.session.session_id}-turn-{turn_no}.jsonl"
        child_report_path = report_dir / f"{self.session.session_id}-turn-{turn_no}.md"
        self.trace.emit("chat_analysis_invoked", session_id=self.session.session_id, turn=turn_no, trace_path=str(child_trace_path), report_path=str(child_report_path))

        child_logger = TraceLogger(child_trace_path, run_id=f"{self.session.session_id}-turn-{turn_no}")
        try:
            agent = WebLogAnalysisAgent(child_logger, use_llm=self.use_llm, llm=self.llm)
            state = agent.run(user_input, self.session.access_log_path, log_format=self.session.log_format)
        finally:
            child_logger.close()

        summary = summarize_analysis_state(state)
        self.session.last_analysis = summary
        self.session.current_focus = summary.get("request", {})
        self.session.summaries.append(render_analysis_summary(summary))
        child_report_path.write_text(state.finalReport or "", encoding="utf-8")
        return render_analysis_summary(summary)

    def _answer_followup(self, user_input: str) -> str:
        context = self.build_chat_context(user_input)
        result = self._llm_followup(context)
        if result:
            return result
        return deterministic_followup_response(context, user_input)

    def _llm_followup(self, context: Dict[str, Any]) -> Optional[str]:
        if not self.use_llm:
            self.trace.emit("llm_skipped", event_id="llm-chat-followup", name="chat_followup", reason="disabled_by_cli")
            return None
        if not self.llm.enabled:
            self.trace.emit("llm_skipped", event_id="llm-chat-followup", name="chat_followup", reason="llm_not_configured_or_missing_api_key", model=self.llm.config.model, config=self.llm.config.sanitized())
            return None
        messages = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ]
        self.trace.emit("llm_start", event_id="llm-chat-followup", name="chat_followup", model=self.llm.config.model, messages=messages)
        try:
            result = self.llm.chat(messages)
            content = result.get("content", "").strip()
            self.trace.emit("llm_end", event_id="llm-chat-followup", name="chat_followup", model=result.get("model"), output=content, usage=result.get("usage"), latency_ms=result.get("latency_ms"))
            return content or None
        except Exception as exc:
            self.trace.emit("llm_error", event_id="llm-chat-followup", name="chat_followup", model=self.llm.config.model, error={"type": exc.__class__.__name__, "message": str(exc)})
            return None
