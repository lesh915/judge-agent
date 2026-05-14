from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .schema import AnalysisResult
from .session import JudgeSessionState


SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


class JudgeChatAgent:
    """Conversation layer that analyzes drift findings, not just prints reports.

    The Simple MVP deliberately keeps this deterministic so it works in CI and on
    developer laptops without API keys. Its interface mirrors a chat agent: it
    keeps session memory, classifies each turn, selects relevant findings, then
    composes an evidence-grounded response.
    """

    def __init__(self, session: JudgeSessionState):
        self.session = session

    def load_analysis(self, results: Iterable[AnalysisResult]) -> None:
        self.session.analysis_results = [result.to_dict() for result in results]
        self.session.focus = self._default_focus()
        self.session.summary = self._build_summary()

    def handle_user_turn(self, user_input: str) -> str:
        self.session.add_turn("user", user_input)
        intent = self._classify_intent(user_input)
        self.session.last_intent = intent
        finding = self._select_finding(user_input)
        if finding:
            self.session.focus = {
                "run_id": finding[0].get("run", {}).get("run_id"),
                "finding_id": finding[1].get("id"),
                "metric": finding[1].get("metric"),
            }
        response = self._respond(intent, user_input, finding)
        self.session.add_turn("assistant", response)
        return response

    def welcome(self) -> str:
        if not self.session.analysis_results:
            return "분석 결과가 아직 없습니다. `chat --traces ...`로 trace를 먼저 로드해주세요."
        return self._build_summary() + "\n\n궁금한 finding ID, metric, 원인, 근거, 수정 우선순위를 물어보시면 이어서 분석할게요."

    def _classify_intent(self, text: str) -> str:
        q = text.lower()
        if any(token in q for token in ["block", "fail", "warning", "통과"]):
            return "gate"
        if any(token in q for token in ["근거", "evidence", "왜", "why"]):
            return "evidence"
        if any(token in q for token in ["수정", "고쳐", "fix", "recommend", "조치", "우선"]):
            return "recommendation"
        if any(token in q for token in ["원인", "root", "cause", "분석"]):
            return "root_cause"
        if any(token in q for token in ["요약", "summary", "전체", "상태"]):
            return "summary"
        return "drilldown"

    def _respond(self, intent: str, user_input: str, selected: Optional[Tuple[Dict[str, Any], Dict[str, Any]]]) -> str:
        if intent == "summary":
            return self._build_summary()
        if intent == "gate":
            return self._gate_analysis()
        if selected:
            run, finding = selected
            if intent == "evidence":
                return self._evidence_response(run, finding)
            if intent == "recommendation":
                return self._recommendation_response(run, finding)
            if intent == "root_cause":
                return self._root_cause_response(run, finding)
            return self._finding_overview(run, finding)
        top = self._top_findings(limit=3)
        if not top:
            return "현재 로드된 trace에서는 drift finding이 없습니다. 정상 baseline으로 보입니다."
        lines = ["어떤 finding을 더 볼지 특정되지 않아서 영향도가 큰 순서로 짚어볼게요."]
        for run, finding in top:
            lines.append(f"- {finding['id']} `{finding['metric']}` ({finding['severity']}) in `{run.get('run_id')}`: {finding['actual']}")
        lines.append("\n예: `JD-001 근거`, `validation_path_coverage 수정 방향`, `왜 block이야?`처럼 물어보시면 됩니다.")
        return "\n".join(lines)

    def _build_summary(self) -> str:
        results = self.session.analysis_results
        run_count = len(results)
        gates = Counter(result.get("gate", "unknown") for result in results)
        findings = [finding for result in results for finding in result.get("findings", [])]
        severities = Counter(finding.get("severity", "unknown") for finding in findings)
        lines = [
            f"총 {run_count}개 run을 분석했습니다.",
            f"Gate: pass {gates.get('pass', 0)}, warning {gates.get('warning', 0)}, block {gates.get('block', 0)}",
            f"Findings: critical {severities.get('critical', 0)}, high {severities.get('high', 0)}, medium {severities.get('medium', 0)}, low {severities.get('low', 0)}",
        ]
        top = self._top_findings(limit=5)
        if top:
            lines.append("\n우선 확인할 항목:")
            for run, finding in top:
                lines.append(f"- {finding['id']} `{finding['metric']}` / {finding['severity']} / run `{run.get('run_id')}`")
        else:
            lines.append("\n현재는 우선 확인할 drift finding이 없습니다.")
        return "\n".join(lines)

    def _gate_analysis(self) -> str:
        blocked = [r for r in self.session.analysis_results if r.get("gate") == "block"]
        warnings = [r for r in self.session.analysis_results if r.get("gate") == "warning"]
        lines = []
        if blocked:
            lines.append("block의 직접 원인은 critical finding이 있는 run입니다.")
            for result in blocked:
                critical = [f for f in result.get("findings", []) if f.get("severity") == "critical"]
                lines.append(f"- `{result.get('run', {}).get('run_id')}` score={result.get('score')} critical={len(critical)}")
                for finding in critical:
                    lines.append(f"  - {finding.get('id')} `{finding.get('metric')}`: {finding.get('actual')}")
        else:
            lines.append("현재 block run은 없습니다.")
        if warnings:
            lines.append("\nwarning run은 high/medium finding 때문에 review가 필요합니다.")
            for result in warnings:
                lines.append(f"- `{result.get('run', {}).get('run_id')}` score={result.get('score')}")
        return "\n".join(lines)

    def _finding_overview(self, run: Dict[str, Any], finding: Dict[str, Any]) -> str:
        return "\n".join([
            f"{finding['id']} `{finding['metric']}` 분석입니다.",
            f"- run: `{run.get('run_id')}`",
            f"- severity/confidence: {finding.get('severity')} / {finding.get('confidence')}",
            f"- expected: {finding.get('expected')}",
            f"- actual: {finding.get('actual')}",
            f"- recommendation: {finding.get('recommendation')}",
        ])

    def _evidence_response(self, run: Dict[str, Any], finding: Dict[str, Any]) -> str:
        lines = [f"{finding['id']} `{finding['metric']}`의 근거입니다."]
        lines.append(f"- run: `{run.get('run_id')}`")
        for item in finding.get("evidence", []):
            lines.append(f"- {item}")
        lines.append("\n이 근거는 trace event와 detector가 남긴 관찰값에서 온 것이고, 추정 원인과는 분리해서 봐야 합니다.")
        return "\n".join(lines)

    def _recommendation_response(self, run: Dict[str, Any], finding: Dict[str, Any]) -> str:
        category = finding.get("category")
        lines = [f"수정 우선순위는 `{finding.get('metric')}`부터 보는 게 맞습니다."]
        lines.append(f"- 이유: severity={finding.get('severity')}, gate 영향 run=`{run.get('run_id')}`")
        lines.append(f"- 직접 조치: {finding.get('recommendation')}")
        if category == "graph":
            lines.append("- 구현 관점: graph edge 조건과 validation node 실행 보장을 테스트로 묶으세요.")
        elif category == "tool":
            lines.append("- 구현 관점: tool 입력을 parsed request/state와 대조하고, 오류율이 높으면 finalization을 막으세요.")
        elif category in {"prompt", "completion"}:
            lines.append("- 구현 관점: final output contract validator를 통과하지 못하면 재생성 또는 실패 처리하세요.")
        elif category == "context":
            lines.append("- 구현 관점: RAG/MCP context가 필요한 task인지 intent에서 판단하고 누락 시 confidence를 낮추세요.")
        return "\n".join(lines)

    def _root_cause_response(self, run: Dict[str, Any], finding: Dict[str, Any]) -> str:
        metric = finding.get("metric")
        cause = {
            "validation_path_coverage": "graph transition이 validation 단계를 우회했거나 validation 결과를 gate 조건으로 강제하지 않은 구조 문제",
            "target_endpoint_consistency": "사용자 요청에서 파싱한 targetPath가 tool argument 생성 단계에 안정적으로 고정되지 않은 문제",
            "metric_result_consistency": "metric 산출이 검증 가능한 tool output이 아니라 내부 상태/환각 값으로 대체된 문제",
            "output_contract_compliance": "prompt/output contract가 finalization 직전에 검증되지 않은 문제",
            "parse_error_handling_score": "parse 실패율이 높은데도 분석을 계속 진행하고 confidence를 낮추거나 실패 처리하지 않은 문제",
        }.get(metric, "trace상 기대 동작과 실제 agent 동작이 어긋난 drift")
        return "\n".join([
            f"가능성이 큰 원인은 {cause}입니다.",
            f"- finding: {finding.get('id')} `{metric}`",
            f"- run: `{run.get('run_id')}`",
            f"- 판단 근거: {finding.get('actual')}",
            f"- 다음 확인: {finding.get('recommendation')}",
        ])

    def _select_finding(self, text: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        q = text.lower()
        focus_metric = str(self.session.focus.get("metric") or "").lower()
        focus_id = str(self.session.focus.get("finding_id") or "").lower()
        candidates = self._all_findings()
        for run, finding in candidates:
            if finding.get("id", "").lower() in q:
                return run, finding
        for run, finding in candidates:
            metric = finding.get("metric", "").lower()
            if metric and metric in q:
                return run, finding
        for run, finding in candidates:
            run_id = str(run.get("run_id", "")).lower()
            if run_id and run_id in q:
                return run, finding
        if focus_metric or focus_id:
            for run, finding in candidates:
                if finding.get("metric", "").lower() == focus_metric or finding.get("id", "").lower() == focus_id:
                    return run, finding
        top = self._top_findings(limit=1)
        return top[0] if top else None

    def _top_findings(self, limit: int) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        candidates = self._all_findings()
        return sorted(candidates, key=lambda item: (SEVERITY_RANK.get(item[1].get("severity"), 0), item[1].get("confidence", 0)), reverse=True)[:limit]

    def _all_findings(self) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for result in self.session.analysis_results:
            run = result.get("run") or {}
            for finding in result.get("findings", []):
                pairs.append((run, finding))
        return pairs

    def _default_focus(self) -> Dict[str, Any]:
        top = self._top_findings(limit=1)
        if not top:
            return {}
        run, finding = top[0]
        return {"run_id": run.get("run_id"), "finding_id": finding.get("id"), "metric": finding.get("metric")}
