from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .schema import AnalysisResult, Finding


def markdown_report(results: List[AnalysisResult]) -> str:
    total = len(results)
    blocks = sum(1 for r in results if r.gate == "block")
    warnings = sum(1 for r in results if r.gate == "warning")
    passes = sum(1 for r in results if r.gate == "pass")
    lines = [
        "# Simple Judge Agent Report",
        "",
        "## Summary",
        "",
        f"- runs: {total}",
        f"- pass: {passes}",
        f"- warning: {warnings}",
        f"- block: {blocks}",
        "",
    ]
    for result in results:
        lines.extend([
            f"## Run `{result.run.run_id}`",
            "",
            f"- gate: **{result.gate}**",
            f"- score: {result.score}",
            f"- agent: {result.run.agent_name or 'unknown'}",
            f"- architecture: {result.run.architecture or 'unknown'}",
            f"- trace: {result.run.artifacts.get('tracePath', '')}",
            "",
            "### Findings",
            "",
        ])
        if not result.findings:
            lines.append("- No drift findings.")
        for finding in result.findings:
            lines.extend([
                f"#### {finding.id} {finding.metric}",
                "",
                f"- category: {finding.category}",
                f"- severity: {finding.severity}",
                f"- confidence: {finding.confidence:.2f}",
                f"- expected: {finding.expected}",
                f"- actual: {finding.actual}",
                "- evidence:",
                *[f"  - {item}" for item in finding.evidence],
                f"- recommendation: {finding.recommendation}",
                "",
            ])
    return "\n".join(lines).rstrip() + "\n"


def write_json(results: List[AnalysisResult], path: str | Path) -> None:
    data = {"results": [result.to_dict() for result in results]}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(results: List[AnalysisResult], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(markdown_report(results), encoding="utf-8")
