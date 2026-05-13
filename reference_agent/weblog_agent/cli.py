from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fixtures import REPORT_DIR, TRACE_DIR, fixtures
from .graph import WebLogAnalysisAgent
from .trace import TraceLogger


def run_fixture(fixture_id: str, output_dir: Path | None = None) -> int:
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
        agent = WebLogAnalysisAgent(logger, fault=fx.fault)
        state = agent.run(fx.user_input, str(fx.access_log_path))
    finally:
        logger.close()
    report_path = report_dir / f"{fixture_id}.md"
    report_path.write_text(state.finalReport or "", encoding="utf-8")
    print(json.dumps({"fixture_id": fixture_id, "trace_path": str(trace_path), "report_path": str(report_path), "status": "ok"}, ensure_ascii=False))
    return 0


def run_all(output_dir: Path | None = None) -> int:
    code = 0
    for fixture_id in fixtures():
        code = max(code, run_fixture(fixture_id, output_dir))
    return code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="weblog-agent", description="Web Log Analysis Reference Agent")
    sub = parser.add_subparsers(dest="command", required=True)
    p_run = sub.add_parser("run-fixture")
    p_run.add_argument("fixture_id")
    p_run.add_argument("--output-dir", type=Path)
    p_all = sub.add_parser("run-all")
    p_all.add_argument("--output-dir", type=Path)
    p_list = sub.add_parser("list-fixtures")
    args = parser.parse_args(argv)
    if args.command == "run-fixture":
        return run_fixture(args.fixture_id, args.output_dir)
    if args.command == "run-all":
        return run_all(args.output_dir)
    if args.command == "list-fixtures":
        print("\n".join(fixtures().keys()))
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
