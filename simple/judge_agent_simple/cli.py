from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path
from typing import List

from .analyzer import analyze_trace, analyze_traces
from .reporter import markdown_report, write_json, write_markdown


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

    args = parser.parse_args(argv)
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
