from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class SimpleEvent:
    id: str
    type: str
    name: Optional[str] = None
    timestamp: Optional[str] = None
    input: Any = None
    output: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SimpleAgentRun:
    run_id: str
    framework: str = "reference-weblog"
    architecture: Optional[str] = None
    agent_name: Optional[str] = None
    agent_version: Optional[str] = None
    graph_version: Optional[str] = None
    user_input: Optional[str] = None
    instructions: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    events: List[SimpleEvent] = field(default_factory=list)
    raw_events: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def raw_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        return [event for event in self.raw_events if event.get("type") == event_type]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["events"] = [event.to_dict() for event in self.events]
        return data


@dataclass
class Finding:
    id: str
    category: str
    metric: str
    severity: str
    confidence: float
    evidence: List[str]
    expected: str
    actual: str
    recommendation: str
    location: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    run: SimpleAgentRun
    findings: List[Finding]
    score: int
    gate: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run": self.run.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
            "score": self.score,
            "gate": self.gate,
        }
