from __future__ import annotations

from typing import Any, Dict, List, Optional

from .conversation_state import ConversationState
from .llm import LlmClient, LlmResult, UnavailableLlmClient
from .metrics import get_metric
from .prompts import build_hybrid_messages, compact_state_summary
from . import tools


class ToolBasedConversationAgent:
    """General conversational runtime over deterministic Judge Agent tools.

    This is the first non-LLM implementation of the planned conversational agent.
    It behaves like a tool-using agent: classify the user task, select one or more
    internal tools, store tool results, maintain focus, and produce a grounded
    response. LLM/hybrid modes can later replace the planner/response synthesizer
    while reusing the same state and tool registry.
    """

    def __init__(self, state: ConversationState):
        self.state = state

    def load_analysis(self, traces: List[str], adapter_name: str = "reference-weblog-jsonl") -> Dict[str, Any]:
        result = tools.load_traces(self.state, traces, adapter_name=adapter_name)
        self.state.record_tool("load_traces", {"traces": traces, "adapter_name": adapter_name}, result)
        return result

    def welcome(self) -> str:
        if not self.state.analysis_results:
            return "분석 결과가 아직 없습니다. `chat --traces ... --mode deterministic-v2`로 trace를 먼저 로드해주세요."
        summary = tools.summarize_findings(self.state)
        return self._summary_response(summary) + "\n\nmetric, finding ID, run 비교, 근거, 수정 우선순위를 자연어로 물어보시면 됩니다."

    def handle_user_turn(self, user_input: str) -> str:
        self.state.add_message("user", user_input)
        plan = self._plan(user_input)
        self.state.plan = plan
        tool_results: List[Dict[str, Any]] = []
        for step in plan:
            result = self._execute_step(step, user_input)
            tool_results.append(result)
            self.state.record_tool(step["tool"], step.get("arguments", {}), result)
        response = self._respond(user_input, plan, tool_results)
        self.state.final_response = response
        self.state.add_message("assistant", response)
        return response

    def _plan(self, text: str) -> List[Dict[str, Any]]:
        q = text.lower()
        metric = self._metric_from_text(q)
        finding_id = self._finding_id_from_text(q)
        if any(token in q for token in ["run 비교", "비교", "compare"]):
            return [{"tool": "compare_runs", "arguments": {}}]
        if any(token in q for token in ["근거", "evidence", "왜", "why"]):
            return [{"tool": "get_evidence", "arguments": {"query": text, "metric": metric, "finding_id": finding_id}}]
        if any(token in q for token in ["수정", "고쳐", "fix", "recommend", "조치", "우선"]):
            return [{"tool": "recommend_fix", "arguments": {"query": text, "metric": metric, "finding_id": finding_id}}]
        if any(token in q for token in ["block", "warning", "fail", "통과", "gate", "실패"]):
            return [{"tool": "explain_gate", "arguments": {}}]
        if metric or finding_id:
            return [{"tool": "get_finding", "arguments": {"query": text, "metric": metric, "finding_id": finding_id}}]
        if any(token in q for token in ["run", "목록", "list"]):
            return [{"tool": "list_runs", "arguments": {}}]
        return [{"tool": "summarize_findings", "arguments": {}}]

    def _execute_step(self, step: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        name = step["tool"]
        args = step.get("arguments") or {}
        if name == "summarize_findings":
            return tools.summarize_findings(self.state)
        if name == "list_runs":
            return tools.list_runs(self.state)
        if name == "get_finding":
            return tools.get_finding(self.state, args.get("query") or user_input, metric=args.get("metric"), finding_id=args.get("finding_id"))
        if name == "get_evidence":
            return tools.get_evidence(self.state, args.get("query") or user_input)
        if name == "recommend_fix":
            return tools.recommend_fix(self.state, args.get("query") or user_input)
        if name == "explain_gate":
            return tools.explain_gate(self.state)
        if name == "compare_runs":
            return tools.compare_runs(self.state)
        return {"tool": name, "error": f"unknown tool: {name}"}

    def _respond(self, user_input: str, plan: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> str:
        if not results:
            return "실행한 tool 결과가 없어 답변할 수 없습니다."
        result = results[-1]
        tool = result.get("tool")
        if tool == "summarize_findings":
            return self._summary_response(result)
        if tool == "list_runs":
            return self._runs_response(result)
        if tool == "compare_runs":
            return self._compare_response(result)
        if tool == "explain_gate":
            return self._gate_response(result)
        if tool == "get_finding":
            return self._finding_response(result)
        if tool == "get_evidence":
            return self._evidence_response(result)
        if tool == "recommend_fix":
            return self._recommendation_response(result)
        return f"tool `{tool}` 결과를 해석하지 못했습니다: {result}"

    def _summary_response(self, result: Dict[str, Any]) -> str:
        lines = [
            f"총 {result.get('run_count', 0)}개 run을 분석했습니다.",
            f"Gate: {result.get('gate_counts', {})}",
            f"Severity: {result.get('severity_counts', {})}",
        ]
        top = result.get("top_findings") or []
        if top:
            lines.append("\n우선 확인할 metric/finding:")
            for finding in top:
                spec = finding.get("metric_spec") or {}
                priority = finding.get("metric_priority")
                priority_text = f", priority={priority}" if priority else ""
                lines.append(f"- {finding.get('id')} `{finding.get('metric')}` ({finding.get('severity')}{priority_text}) — {spec.get('category') or finding.get('category')}")
        else:
            lines.append("\n현재 drift finding은 없습니다.")
        return "\n".join(lines)

    def _runs_response(self, result: Dict[str, Any]) -> str:
        runs = result.get("runs") or []
        if not runs:
            return "로드된 run이 없습니다."
        lines = ["로드된 run 목록입니다."]
        for run in runs:
            lines.append(f"- `{run.get('run_id')}` gate={run.get('gate')} score={run.get('score')} findings={run.get('finding_count')}")
        return "\n".join(lines)

    def _compare_response(self, result: Dict[str, Any]) -> str:
        runs = result.get("runs") or []
        if not runs:
            return "비교할 run이 없습니다."
        lines = ["run 위험도를 비교하면 다음 순서입니다."]
        for run in runs:
            lines.append(f"- `{run.get('run_id')}`: gate={run.get('gate')}, score={run.get('score')}, findings={run.get('finding_count')}")
        return "\n".join(lines)

    def _gate_response(self, result: Dict[str, Any]) -> str:
        if not result.get("blocked") and not result.get("warnings"):
            return "현재 block/warning run은 없습니다. gate 기준으로는 pass 상태입니다."
        lines = [f"Gate 이슈: block {result.get('blocked', 0)}개, warning {result.get('warnings', 0)}개입니다."]
        for reason in result.get("reasons", []):
            lines.append(f"- `{reason.get('run_id')}` gate={reason.get('gate')} score={reason.get('score')}")
            for finding in reason.get("findings", []):
                priority = finding.get("metric_priority")
                p = f", priority={priority}" if priority else ""
                lines.append(f"  - {finding.get('id')} `{finding.get('metric')}` ({finding.get('severity')}{p}): {finding.get('actual')}")
        return "\n".join(lines)

    def _finding_response(self, result: Dict[str, Any]) -> str:
        if not result.get("found"):
            return "해당 finding/metric을 찾지 못했습니다. metric 이름이나 finding ID를 다시 알려주세요."
        finding = result["finding"]
        run = result.get("run") or {}
        spec = finding.get("metric_spec") or {}
        return "\n".join([
            f"{finding.get('id')} `{finding.get('metric')}` 분석입니다.",
            f"- run: `{run.get('run_id')}`",
            f"- category: {spec.get('category') or finding.get('category')}",
            f"- severity/confidence: {finding.get('severity')} / {finding.get('confidence')}",
            f"- priority: {finding.get('metric_priority')}",
            f"- expected: {finding.get('expected')}",
            f"- actual: {finding.get('actual')}",
            f"- recommendation: {finding.get('recommendation')}",
        ])

    def _evidence_response(self, result: Dict[str, Any]) -> str:
        if not result.get("found"):
            return "근거를 찾을 finding/metric을 특정하지 못했습니다."
        finding = result.get("finding") or {}
        lines = [f"{finding.get('id')} `{finding.get('metric')}`의 근거입니다."]
        for item in result.get("evidence", []):
            lines.append(f"- {item.get('item')}")
        lines.append("\n이 답변은 finding evidence와 metric registry에 grounded 되어 있습니다.")
        return "\n".join(lines)

    def _recommendation_response(self, result: Dict[str, Any]) -> str:
        if not result.get("found"):
            return "수정 방향을 제안할 finding/metric을 찾지 못했습니다."
        lines = [f"`{result.get('metric')}` 수정 우선순위입니다."]
        lines.append(f"- severity: {result.get('severity')}, priority: {result.get('priority')}, category: {result.get('category')}")
        lines.append(f"- 직접 조치: {result.get('recommendation')}")
        evidence = result.get("evidence") or []
        if evidence:
            lines.append("- 근거:")
            for item in evidence[:3]:
                lines.append(f"  - {item}")
        return "\n".join(lines)

    def _metric_from_text(self, q: str) -> Optional[str]:
        tokens = [token.strip("`.,:;!?()[]{}\"'") for token in q.split()]
        for token in tokens:
            if get_metric(token):
                return token
        # Also handle Korean text containing full metric names without spaces.
        for metric in self.state.metric_history:
            if metric and metric.lower() in q:
                return metric
        return None

    def _finding_id_from_text(self, q: str) -> Optional[str]:
        for token in q.replace("`", " ").replace(",", " ").split():
            upper = token.upper().strip(".,:;!?()[]{}")
            if upper.startswith("JD-"):
                return upper
        return None


class HybridConversationAgent(ToolBasedConversationAgent):
    """Hybrid runtime: deterministic tools + optional LLM response synthesis.

    Planning and tool execution remain deterministic. The LLM only rewrites and
    explains the grounded tool results. If no provider is configured, the agent
    returns the deterministic answer with an explicit fallback note.
    """

    def __init__(self, state: ConversationState, llm: Optional[LlmClient] = None):
        super().__init__(state)
        self.llm = llm or UnavailableLlmClient()
        self.last_llm_result: Optional[LlmResult] = None

    def welcome(self) -> str:
        base = super().welcome()
        return base + "\n\nHybrid mode: deterministic tools로 근거를 수집하고, LLM이 설정된 경우 답변 표현만 합성합니다."

    def _respond(self, user_input: str, plan: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> str:
        deterministic = super()._respond(user_input, plan, results)
        messages = build_hybrid_messages(user_input, deterministic, results, compact_state_summary(self.state))
        llm_result = self.llm.complete(messages, temperature=0.0)
        self.last_llm_result = llm_result
        if llm_result.used_fallback or not llm_result.content.strip():
            return deterministic + "\n\n[hybrid fallback] LLM provider가 설정되지 않아 deterministic tool 결과로 답변했습니다."
        return llm_result.content.strip()
