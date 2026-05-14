from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .chat_agent import ChatAgent
from .fixtures import FIXTURE_DIR, REPORT_DIR, TRACE_DIR, fixtures
from .graph import WebLogAnalysisAgent
from .session import ChatSessionState, list_sessions, load_session, new_session_id, save_session
from .trace import TraceLogger


def run_fixture(fixture_id: str, output_dir: Path | None = None, use_llm: bool = True) -> int:
    all_fixtures = fixtures()
    if fixture_id not in all_fixtures:
        print(f"Unknown fixture: {fixture_id}")
        print("Available:", ", ".join(sorted(all_fixtures)))
        return 2
    fx = all_fixtures[fixture_id]
    trace_dir = output_dir or TRACE_DIR
    report_dir = REPORT_DIR if output_dir is None else output_dir / "reports"
    trace_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / f"{fixture_id}.jsonl"
    logger = TraceLogger(trace_path, run_id=fixture_id)
    try:
        agent = WebLogAnalysisAgent(logger, fault=fx.fault, use_llm=use_llm)
        state = agent.run(fx.user_input, str(fx.access_log_path))
    finally:
        logger.close()
    report_path = report_dir / f"{fixture_id}.md"
    report_path.write_text(state.finalReport or "", encoding="utf-8")
    print(json.dumps({"fixture_id": fixture_id, "trace_path": str(trace_path), "report_path": str(report_path), "status": "ok"}, ensure_ascii=False))
    return 0


def run_all(output_dir: Path | None = None, use_llm: bool = True) -> int:
    code = 0
    for fixture_id in fixtures():
        code = max(code, run_fixture(fixture_id, output_dir, use_llm=use_llm))
    return code


def run_analysis(user_input: str, access_log: Path, trace_path: Path, report_path: Path, use_llm: bool = True) -> int:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    logger = TraceLogger(trace_path)
    try:
        agent = WebLogAnalysisAgent(logger, use_llm=use_llm)
        state = agent.run(user_input, str(access_log))
    finally:
        logger.close()
    report_path.write_text(state.finalReport or "", encoding="utf-8")
    print(json.dumps({"run_id": logger.run_id, "trace_path": str(trace_path), "report_path": str(report_path), "status": "ok"}, ensure_ascii=False))
    return 0


def run_chat(
    access_log: Path,
    session_id: str | None = None,
    new_session: bool = False,
    session_dir: Path | None = None,
    trace_dir: Path | None = None,
    report_dir: Path | None = None,
    use_llm: bool = True,
) -> int:
    session_dir = session_dir or (TRACE_DIR.parent / "sessions")
    trace_dir = trace_dir or TRACE_DIR
    report_dir = report_dir or REPORT_DIR
    if session_id and not new_session:
        try:
            session = load_session(session_id, session_dir=session_dir)
            if access_log:
                session.access_log_path = str(access_log)
        except FileNotFoundError:
            session = ChatSessionState(session_id=session_id, access_log_path=str(access_log))
    else:
        session = ChatSessionState(session_id=session_id or new_session_id(), access_log_path=str(access_log))
    save_session(session, session_dir=session_dir)

    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / f"{session.session_id}-chat.jsonl"
    logger = TraceLogger(trace_path, run_id=session.session_id)
    try:
        agent = ChatAgent(session, logger, use_llm=use_llm, session_dir=session_dir)
        agent.start()
        print(json.dumps({"session_id": session.session_id, "trace_path": str(trace_path), "session_path": str(save_session(session, session_dir=session_dir)), "status": "ready"}, ensure_ascii=False))
        print("Type /exit to quit, /help for commands.")
        for raw in sys.stdin:
            user_input = raw.strip()
            if not user_input:
                continue
            if user_input in {"/exit", "/quit"}:
                break
            if user_input == "/help":
                print("Commands: /exit, /help, /summary, /reset")
                continue
            if user_input == "/summary":
                print(session.summaries[-1] if session.summaries else "No analysis summary is available yet.")
                continue
            if user_input == "/reset":
                session.turns.clear()
                session.current_focus.clear()
                session.last_analysis = None
                session.summaries.clear()
                save_session(session, session_dir=session_dir)
                print("Session context reset.")
                continue
            response = agent.handle_user_turn(user_input, report_dir=report_dir, trace_dir=trace_dir)
            print(response)
        agent.end()
    finally:
        logger.close()
        save_session(session, session_dir=session_dir)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="weblog-agent", description="Web Log Analysis Reference Agent")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run-fixture")
    p_run.add_argument("fixture_id")
    p_run.add_argument("--output-dir", type=Path)
    p_run.add_argument("--no-llm", action="store_true", help="Disable LLM calls and use deterministic fallback logic")
    p_all = sub.add_parser("run-all")
    p_all.add_argument("--output-dir", type=Path)
    p_all.add_argument("--no-llm", action="store_true", help="Disable LLM calls and use deterministic fallback logic")
    p_analyze = sub.add_parser("analyze", help="Run the agent on a custom user request and access log")
    p_analyze.add_argument("--input", required=True, help="User analysis request")
    p_analyze.add_argument("--access-log", type=Path, default=FIXTURE_DIR / "access.log")
    p_analyze.add_argument("--trace-out", type=Path, default=TRACE_DIR / "custom-run.jsonl")
    p_analyze.add_argument("--report-out", type=Path, default=REPORT_DIR / "custom-run.md")
    p_analyze.add_argument("--no-llm", action="store_true", help="Disable LLM calls and use deterministic fallback logic")
    p_chat = sub.add_parser("chat", help="Start an interactive context-aware chat session")
    p_chat.add_argument("--access-log", type=Path, default=FIXTURE_DIR / "access.log")
    p_chat.add_argument("--session-id", help="Resume or create a named chat session")
    p_chat.add_argument("--new-session", action="store_true", help="Start a fresh session even if --session-id already exists")
    p_chat.add_argument("--session-dir", type=Path, help="Directory for persisted chat sessions")
    p_chat.add_argument("--trace-dir", type=Path, help="Directory for chat and analysis traces")
    p_chat.add_argument("--report-dir", type=Path, help="Directory for generated analysis reports")
    p_chat.add_argument("--no-llm", action="store_true", help="Disable LLM calls and use deterministic fallback logic")
    p_sessions = sub.add_parser("list-sessions", help="List persisted chat sessions")
    p_sessions.add_argument("--session-dir", type=Path, default=TRACE_DIR.parent / "sessions")
    p_list = sub.add_parser("list-fixtures")
    args = parser.parse_args(argv)
    if args.command == "run-fixture":
        return run_fixture(args.fixture_id, args.output_dir, use_llm=not args.no_llm)
    if args.command == "run-all":
        return run_all(args.output_dir, use_llm=not args.no_llm)
    if args.command == "analyze":
        return run_analysis(args.input, args.access_log, args.trace_out, args.report_out, use_llm=not args.no_llm)
    if args.command == "chat":
        return run_chat(args.access_log, args.session_id, args.new_session, args.session_dir, args.trace_dir, args.report_dir, use_llm=not args.no_llm)
    if args.command == "list-sessions":
        print(json.dumps(list_sessions(args.session_dir), ensure_ascii=False))
        return 0
    if args.command == "list-fixtures":
        print("\n".join(fixtures().keys()))
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
