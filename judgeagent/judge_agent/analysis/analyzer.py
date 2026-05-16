from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Union

from ..adapters.reference import ReferenceAgentJsonlAdapter
from .detectors import ReferenceWebLogDetector, gate_for, score_findings
from ..core.config import app_config
from ..core.schema import AnalysisResult

APP_DEFAULTS = app_config()["defaults"]


def analyze_trace(path: Union[str, Path], adapter_name: Optional[str] = None) -> AnalysisResult:
    adapter_name = adapter_name or APP_DEFAULTS["adapter"]
    if adapter_name != APP_DEFAULTS["adapter"]:
        raise ValueError(f"unsupported adapter for MVP: {adapter_name}")
    run = ReferenceAgentJsonlAdapter().load(path)
    findings = ReferenceWebLogDetector().detect(run)
    score = score_findings(findings)
    gate = gate_for(score, findings)
    return AnalysisResult(run=run, findings=findings, score=score, gate=gate)


def analyze_traces(paths: Iterable[Union[str, Path]], adapter_name: Optional[str] = None) -> List[AnalysisResult]:
    return [analyze_trace(path, adapter_name=adapter_name) for path in paths]
