from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class DriftMetricSpec:
    name: str
    category: str
    measurement_method: str
    value_type: str
    description: str
    severity: str
    mvp_priority: Optional[int] = None
    ref_agent_priority: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


# Source: docs/DRIFT_METRICS.xlsx (전체 Metric 목록, MVP 우선순위, Ref Agent 우선순위)
_METRICS: List[DriftMetricSpec] = [
    DriftMetricSpec("instruction_adherence_score", "Prompt / Instruction", "LLM judge + rule", "0.0 ~ 1.0", "Agent가 주어진 instruction을 따른 정도.", "High", 6),
    DriftMetricSpec("output_format_compliance", "Prompt / Instruction", "deterministic parser", "pass/fail", "요구된 output format을 지켰는지.", "Medium"),
    DriftMetricSpec("prompt_template_version_present", "Prompt / Instruction", "trace 검사", "존재 여부", "trace에 prompt template 이름/version이 기록되어 있는지.", "Low"),
    DriftMetricSpec("tool_selection_accuracy", "Tool Use", "exact match / LLM judge", "0.0 ~ 1.0", "선택한 tool이 task에 적절했는지.", "High"),
    DriftMetricSpec("tool_argument_correctness", "Tool Use", "rule (schema + context)", "0.0 ~ 1.0", "tool argument가 schema와 context를 만족하는지.", "High", 1),
    DriftMetricSpec("tool_error_handling_score", "Tool Use", "rule", "0.0 ~ 1.0", "tool error를 적절히 처리했는지.", "Critical", 2),
    DriftMetricSpec("redundant_tool_call_count", "Tool Use", "rule (중복 탐지)", "count (정수)", "같은 목적의 중복 tool 호출 횟수.", "Medium", 7),
    DriftMetricSpec("tool_result_grounding_score", "Tool Use", "LLM judge + rule", "0.0 ~ 1.0", "final output이 tool result와 일치하는지.", "High"),
    DriftMetricSpec("retrieval_context_relevance", "Context / Retrieval", "LLM judge / embedding sim", "0.0 ~ 1.0", "retriever가 가져온 document/chunk가 user input과 관련 있는지.", "Medium"),
    DriftMetricSpec("retrieval_context_precision", "Context / Retrieval", "rule (비율)", "0.0 ~ 1.0", "retrieved chunk 중 관련 있는 chunk의 비율.", "Medium"),
    DriftMetricSpec("answer_context_groundedness", "Context / Retrieval", "LLM judge", "0.0 ~ 1.0", "final output이 retrieved context에 근거하는지.", "High", 3),
    DriftMetricSpec("missing_required_context", "Context / Retrieval", "reference fixture / LLM judge", "0.0 ~ 1.0", "답변에 필요한 context가 검색되지 않았는지.", "High"),
    DriftMetricSpec("memory_claim_supported", "Memory / State", "rule (state 조회)", "pass/fail", "agent가 '기억한다'고 주장한 내용이 memory/state에 존재하는지.", "High"),
    DriftMetricSpec("state_freshness_score", "Memory / State", "rule (timestamp/version)", "0.0 ~ 1.0", "LangGraph state/checkpoint가 최신인지.", "Medium"),
    DriftMetricSpec("state_value_grounding", "Memory / State", "rule (event 추적)", "0.0 ~ 1.0", "node가 사용한 state 값이 이전 event에서 생성/검증된 값인지.", "High"),
    DriftMetricSpec("memory_update_correctness", "Memory / State", "rule", "pass/fail", "저장해야 할 memory를 저장했고, 저장하면 안 되는 내용을 저장하지 않았는지.", "Medium"),
    DriftMetricSpec("node_sequence_correctness", "LangGraph Flow", "rule (expected path)", "0.0 ~ 1.0", "실행된 node 순서가 기대 workflow와 맞는지.", "Critical", 4),
    DriftMetricSpec("edge_decision_correctness", "LangGraph Flow", "rule (state 비교)", "0.0 ~ 1.0", "conditional edge 선택이 state/tool result와 맞는지.", "High"),
    DriftMetricSpec("node_loop_count", "LangGraph Flow", "rule (반복 탐지)", "count (정수)", "같은 node 반복 횟수.", "Medium"),
    DriftMetricSpec("graph_completion_path_valid", "LangGraph Flow", "rule (종료 path)", "pass/fail", "종료 node까지의 path가 정상 완료 path인지.", "High"),
    DriftMetricSpec("required_checkpoint_present", "LangGraph Flow", "rule (checkpoint 검사)", "pass/fail", "중요 node 이후 checkpoint/state snapshot이 존재하는지.", "Medium"),
    DriftMetricSpec("task_completion_score", "Final Output / Completion", "LLM judge + rule", "0.0 ~ 1.0", "사용자 요청이 완료되었는지.", "High"),
    DriftMetricSpec("verification_coverage", "Final Output / Completion", "rule", "0.0 ~ 1.0", "완료 전 필요한 검증을 수행했는지.", "High", 5),
    DriftMetricSpec("final_answer_consistency", "Final Output / Completion", "LLM judge + rule", "0.0 ~ 1.0", "final answer가 trace의 실제 실행 결과와 일치하는지.", "High"),
    DriftMetricSpec("hallucinated_completion_claim", "Final Output / Completion", "LLM judge + rule", "pass/fail", "실제로 수행하지 않은 일을 완료했다고 말했는지.", "Critical"),
    DriftMetricSpec("react_step_completeness", "ReAct / RAG / MCP", "rule + LLM judge", "0.0 ~ 1.0", "Thought/Action/Observation sequence가 완전한가.", "High"),
    DriftMetricSpec("action_grounding_score", "ReAct / RAG / MCP", "rule + LLM judge", "0.0 ~ 1.0", "action argument가 user input/state/observation에서 근거를 갖는가.", "High"),
    DriftMetricSpec("observation_utilization_score", "ReAct / RAG / MCP", "LLM judge", "0.0 ~ 1.0", "tool observation이 다음 reasoning/final report에 반영되는가.", "Medium"),
    # Reference weblog agent fixture-specific metrics.
    DriftMetricSpec("output_contract_compliance", "Prompt / Instruction", "deterministic parser", "pass/fail", "final output이 markdown contract를 만족하는지.", "High", None, 1),
    DriftMetricSpec("target_endpoint_consistency", "Tool Use", "rule (context)", "pass/fail", "사용자 요청 target endpoint와 tool/metric path가 일치하는지.", "High", None, 2),
    DriftMetricSpec("metric_result_consistency", "Final Output / Completion", "rule (tool output)", "pass/fail", "metric claim이 검증 가능한 tool output에서 왔는지.", "High", None, 3),
    DriftMetricSpec("validation_path_coverage", "LangGraph Flow", "rule (expected path)", "pass/fail", "validate_findings node와 validation_result가 실행되었는지.", "Critical", None, 4),
    DriftMetricSpec("parse_error_handling_score", "Tool Use", "rule", "0.0 ~ 1.0", "높은 parse error ratio를 차단/반영했는지.", "High", None, 5),
    DriftMetricSpec("rag_context_presence_and_usage", "Context / Retrieval", "rule", "pass/fail", "RAG retrieval과 final report 반영 여부.", "Medium", None, 6),
    DriftMetricSpec("mcp_context_presence_and_usage", "ReAct / RAG / MCP", "rule", "pass/fail", "MCP service context 수집과 final report 반영 여부.", "Medium", None, 7),
    DriftMetricSpec("chat_context_grounding", "Context / Retrieval", "rule", "pass/fail", "후속 대화가 직전 analysis/focus/evidence에 grounded 되었는지.", "Medium", None, 8),
]

METRIC_REGISTRY: Dict[str, DriftMetricSpec] = {metric.name: metric for metric in _METRICS}


def get_metric(name: str) -> Optional[DriftMetricSpec]:
    return METRIC_REGISTRY.get(name)


def require_metric(name: str) -> DriftMetricSpec:
    metric = get_metric(name)
    if metric is None:
        raise KeyError(f"unknown drift metric: {name}")
    return metric


def list_metrics(category: Optional[str] = None) -> List[DriftMetricSpec]:
    metrics = list(METRIC_REGISTRY.values())
    if category:
        metrics = [metric for metric in metrics if metric.category == category]
    return sorted(metrics, key=metric_sort_key)


def metric_sort_key(metric: DriftMetricSpec) -> tuple:
    priority = metric.mvp_priority if metric.mvp_priority is not None else metric.ref_agent_priority
    return (priority is None, priority or 999, metric.category, metric.name)


def enrich_finding(finding: dict) -> dict:
    metric = get_metric(str(finding.get("metric") or ""))
    if not metric:
        return dict(finding)
    enriched = dict(finding)
    enriched["metric_spec"] = metric.to_dict()
    enriched.setdefault("category", metric.category)
    enriched.setdefault("severity", metric.severity.lower())
    enriched["metric_category"] = metric.category
    enriched["metric_priority"] = metric.mvp_priority or metric.ref_agent_priority
    return enriched


def known_metric_names() -> List[str]:
    return sorted(METRIC_REGISTRY)


def validate_metric_coverage(metric_names: Iterable[str]) -> List[str]:
    return sorted({name for name in metric_names if name not in METRIC_REGISTRY})
