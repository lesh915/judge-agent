from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import List

from .analysis.analyzer import analyze_trace, analyze_traces
from .conversation.legacy import JudgeChatAgent
from .conversation.agent import HybridConversationAgent, ToolBasedConversationAgent
from .conversation.state import ConversationState, load_conversation_state, save_conversation_state
from .conversation.graph import GraphConversationAgent
from .llm.clients import create_llm_client
from .analysis.reporter import markdown_report, write_json, write_markdown
from .core.session import JudgeSessionState, load_session, save_session


def _configure_output_encoding() -> None:
    """Use UTF-8 so Korean reports/JSON do not fail on non-UTF-8 Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass


def _strip_shell_quotes(value: str) -> str:
    # Windows cmd.exe does not treat single quotes as quoting characters.
    # Accept both forms so examples copied from POSIX shells still work.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def expand_trace_args(values: List[str]) -> List[str]:
    paths: List[str] = []
    for value in values:
        value = _strip_shell_quotes(value)
        matches = sorted(glob.glob(value))
        paths.extend(matches or [value])
    return paths


def run_chat(args) -> int:
    if args.mode in {"deterministic-v2", "hybrid", "graph"}:
        return run_conversation_chat(args)

    session_dir = args.session_dir
    if args.resume:
        try:
            session = load_session(session_dir, args.session_id)
        except FileNotFoundError:
            session = JudgeSessionState(session_id=args.session_id)
    else:
        session = JudgeSessionState(session_id=args.session_id)

    agent = JudgeChatAgent(session)
    if args.traces:
        traces = expand_trace_args(args.traces)
        results = analyze_traces(traces, adapter_name=args.adapter)
        agent.load_analysis(results)
    print(json.dumps({"session_id": session.session_id, "session_path": str(save_session(session_dir, session)), "status": "ready", "mode": args.mode}, ensure_ascii=False))
    print(agent.welcome())
    print("Commands: /summary, /findings, /runs, /exit")
    for raw in sys.stdin:
        user_input = raw.strip()
        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            break
        if user_input == "/summary":
            response = agent.handle_user_turn("전체 요약")
        elif user_input == "/findings":
            response = agent.handle_user_turn("finding 전체와 우선순위")
        elif user_input == "/runs":
            lines = []
            for result in session.analysis_results:
                run = result.get("run", {})
                lines.append(f"- `{run.get('run_id')}` gate={result.get('gate')} score={result.get('score')} findings={len(result.get('findings', []))}")
            response = "\n".join(lines) if lines else "로드된 run이 없습니다."
        else:
            response = agent.handle_user_turn(user_input)
        print(response)
        save_session(session_dir, session)
    save_session(session_dir, session)
    return 0


def run_conversation_chat(args) -> int:
    session_dir = args.session_dir
    if args.resume:
        try:
            state = load_conversation_state(session_dir, args.session_id)
        except FileNotFoundError:
            state = ConversationState(session_id=args.session_id)
    else:
        state = ConversationState(session_id=args.session_id)

    if args.mode == "graph":
        agent = GraphConversationAgent(state, llm=create_llm_client(args.llm_provider, args.llm_model, env_file=args.env_file, base_url=args.llm_base_url, api_key=args.llm_api_key), require_langgraph=args.require_langgraph)
    elif args.mode == "hybrid":
        agent = HybridConversationAgent(state, llm=create_llm_client(args.llm_provider, args.llm_model, env_file=args.env_file, base_url=args.llm_base_url, api_key=args.llm_api_key))
    else:
        agent = ToolBasedConversationAgent(state)
    if args.traces:
        traces = expand_trace_args(args.traces)
        agent.load_analysis(traces, adapter_name=args.adapter)
    session_path = save_conversation_state(session_dir, state)
    print(json.dumps({"session_id": state.session_id, "session_path": str(session_path), "status": "ready", "mode": args.mode}, ensure_ascii=False))
    print(agent.welcome())
    print("Commands: /summary, /findings, /runs, /compare, /exit")
    for raw in sys.stdin:
        user_input = raw.strip()
        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            break
        if user_input == "/summary":
            response = agent.handle_user_turn("전체 요약")
        elif user_input == "/findings":
            response = agent.handle_user_turn("finding 전체와 우선순위")
        elif user_input == "/runs":
            response = agent.handle_user_turn("run 목록")
        elif user_input == "/compare":
            response = agent.handle_user_turn("run 비교")
        else:
            response = agent.handle_user_turn(user_input)
        print(response)
        save_conversation_state(session_dir, state)
    save_conversation_state(session_dir, state)
    return 0


def main(argv=None) -> int:
    _configure_output_encoding()
    parser = argparse.ArgumentParser(prog="judge-agent-simple", description="Simple Judge Agent MVP for reference weblog traces")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Analyze one trace")
    p_analyze.add_argument("--trace", required=True)
    p_analyze.add_argument("--adapter", default="reference-weblog-jsonl")
    p_analyze.add_argument("--output", type=Path)
    p_analyze.add_argument("--json", type=Path)
    p_analyze.add_argument("--fail-on", choices=["low", "medium", "high", "critical"], default="critical")

    p_batch = sub.add_parser("analyze-batch", help="Analyze multiple traces")
    p_batch.add_argument("--traces", nargs="+", required=True)
    p_batch.add_argument("--adapter", default="reference-weblog-jsonl")
    p_batch.add_argument("--output", type=Path)
    p_batch.add_argument("--json", type=Path)
    p_batch.add_argument("--fail-on", choices=["low", "medium", "high", "critical"], default="critical")

    p_chat = sub.add_parser("chat", help="Start a conversational judge agent over analyzed traces")
    p_chat.add_argument("--traces", nargs="+", help="Trace JSONL files or glob patterns to analyze before chat starts")
    p_chat.add_argument("--adapter", default="reference-weblog-jsonl")
    p_chat.add_argument("--session-id", default="default")
    p_chat.add_argument("--session-dir", type=Path, default=Path("artifacts/simple-judge/sessions"))
    p_chat.add_argument("--resume", action="store_true", help="Resume a saved judge chat session")
    p_chat.add_argument("--mode", choices=["deterministic", "deterministic-v2", "hybrid", "graph"], default="deterministic", help="Chat runtime mode. deterministic keeps the legacy responder; deterministic-v2 uses tool-based conversation state; hybrid adds optional LLM synthesis; graph uses optional LangGraph runtime with fallback.")
    p_chat.add_argument("--llm-provider", default="auto", help="LLM provider for hybrid/graph mode: auto, openai, openai-compatible, local, vllm, lmstudio, ollama, mock, or none")
    p_chat.add_argument("--llm-model", help="LLM model name for hybrid/graph mode")
    p_chat.add_argument("--llm-base-url", help="OpenAI-compatible base URL, e.g. http://localhost:1234/v1")
    p_chat.add_argument("--llm-api-key", help="LLM API key. For local compatible servers this can be any non-empty value if auth is disabled.")
    p_chat.add_argument("--env-file", help="Path to .env file. Defaults to ./.env or ./simple/.env when present.")
    p_chat.add_argument("--require-langgraph", action="store_true", help="Fail graph mode if LangGraph is not installed instead of falling back to hybrid runtime")

    args = parser.parse_args(argv)
    if args.command == "chat":
        return run_chat(args)
    if args.command == "analyze":
        results = [analyze_trace(args.trace, adapter_name=args.adapter)]
    else:
        traces = expand_trace_args(args.traces)
        results = analyze_traces(traces, adapter_name=args.adapter)

    if args.output:
        write_markdown(results, args.output)
    if args.json:
        write_json(results, args.json)
    if not args.output and not args.json:
        print(markdown_report(results))

    severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    threshold = severity_order[args.fail_on]
    should_fail = any(severity_order.get(f.severity, 0) >= threshold for r in results for f in r.findings)
    return 1 if should_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
