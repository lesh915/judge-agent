from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fixtures import FIXTURE_DIR, REPORT_DIR, TRACE_DIR, fixtures
from .graph import WebLogAnalysisAgent
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
    p_list = sub.add_parser("list-fixtures")
    args = parser.parse_args(argv)
    if args.command == "run-fixture":
        return run_fixture(args.fixture_id, args.output_dir, use_llm=not args.no_llm)
    if args.command == "run-all":
        return run_all(args.output_dir, use_llm=not args.no_llm)
    if args.command == "analyze":
        return run_analysis(args.input, args.access_log, args.trace_out, args.report_out, use_llm=not args.no_llm)
    if args.command == "list-fixtures":
        print("\n".join(fixtures().keys()))
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
