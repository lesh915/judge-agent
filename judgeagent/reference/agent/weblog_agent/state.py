from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WebLogAnalysisState:
    request: Dict[str, Any] = field(default_factory=lambda: {"rawUserInput": "", "requestedMetrics": []})
    logSource: Dict[str, Any] = field(default_factory=dict)
    rawLogs: Optional[Dict[str, Any]] = None
    parsedRecords: List[Dict[str, Any]] = field(default_factory=list)
    filteredRecords: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    baseline: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=lambda: {"logLines": [], "metricRefs": []})
    ragContext: List[Dict[str, Any]] = field(default_factory=list)
    mcpContext: Dict[str, Any] = field(default_factory=dict)
    reactSteps: List[Dict[str, Any]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=lambda: {"passed": False, "issues": []})
    finalReport: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "request": self.request,
            "logSource": self.logSource,
            "rawLogs": None if self.rawLogs is None else {
                "lineCount": self.rawLogs.get("lineCount", 0),
                "truncated": self.rawLogs.get("truncated", False),
            },
            "parsedRecordCount": len(self.parsedRecords),
            "filteredRecordCount": len(self.filteredRecords),
            "metrics": self.metrics,
            "baseline": self.baseline,
            "anomalies": self.anomalies,
            "evidence": self.evidence,
            "ragContextCount": len(self.ragContext),
            "mcpContext": self.mcpContext,
            "reactStepCount": len(self.reactSteps),
            "validation": self.validation,
            "errors": self.errors,
            "finalReportPresent": bool(self.finalReport),
        }
