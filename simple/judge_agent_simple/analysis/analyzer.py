from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

from ..adapters.reference import ReferenceAgentJsonlAdapter
from .detectors import ReferenceWebLogDetector, gate_for, score_findings
from ..core.schema import AnalysisResult


def analyze_trace(path: Union[str, Path], adapter_name: str = "reference-weblog-jsonl") -> AnalysisResult:
    if adapter_name != "reference-weblog-jsonl":
        raise ValueError(f"unsupported adapter for MVP: {adapter_name}")
    run = ReferenceAgentJsonlAdapter().load(path)
    findings = ReferenceWebLogDetector().detect(run)
    score = score_findings(findings)
    gate = gate_for(score, findings)
    return AnalysisResult(run=run, findings=findings, score=score, gate=gate)


def analyze_traces(paths: Iterable[Union[str, Path]], adapter_name: str = "reference-weblog-jsonl") -> List[AnalysisResult]:
    return [analyze_trace(path, adapter_name=adapter_name) for path in paths]
