# Simple Architecture: LangChain/LangGraph Judge Agent

## 1. 목적

이 문서는 LangChain/LangGraph agent를 대상으로 한 심플한 Judge Agent 아키텍처를 정의한다.

범위:

- trace 수집
- event 정규화
- metric 계산
- drift 탐지
- finding 분석
- report 생성
- CI 연동

## 2. 전체 구조

```text
LangChain / LangGraph Agent
        │
        ▼
LangSmith Trace 또는 JSONL Trace
        │
        ▼
Trace Adapter
        │
        ▼
SimpleAgentRun Normalizer
        │
        ▼
Metric Calculators
        │
        ▼
Rule Checkers + LLM Judges
        │
        ▼
Finding Aggregator
        │
        ▼
Markdown / JSON Report
        │
        ▼
CI Gate 또는 개발자 리뷰
```

## 3. 주요 컴포넌트

## 3.1 Trace Sources

초기 지원 trace source:

1. LangSmith run export
2. LangChain callback JSONL
3. LangGraph custom event JSONL

## 3.2 Adapters

Adapter는 외부 trace를 내부 schema로 변환한다.

```ts
interface TraceAdapter {
  name: string;
  canHandle(input: unknown): boolean;
  normalize(input: unknown): SimpleAgentRun;
}
```

초기 adapter:

- `LangSmithAdapter`
- `LangChainJsonlAdapter`
- `LangGraphJsonlAdapter`

## 3.3 Normalizer

역할:

- event timestamp 정렬
- parent-child 관계 복원
- tool start/end 병합
- LangGraph node/edge 정리
- final output 추출
- 누락 필드 확인

## 3.4 Metric Calculators

초기 metric:

- `instruction_adherence_score`
- `tool_argument_correctness`
- `tool_error_handling_score`
- `retrieval_context_relevance`
- `answer_context_groundedness`
- `node_sequence_correctness`
- `verification_coverage`

## 3.5 Rule Checkers

Rule checker는 결정적으로 판단 가능한 drift를 탐지한다.

초기 checker:

- `ToolArgumentChecker`
- `ToolErrorChecker`
- `RepeatedToolCallChecker`
- `NodeSequenceChecker`
- `MissingVerificationChecker`

## 3.6 LLM Judges

LLM judge는 rubric 기반으로 품질을 평가한다.

초기 judge:

- `ContextGroundingJudge`
- `InstructionAdherenceJudge`
- `TaskCompletionJudge`

## 3.7 Finding Aggregator

역할:

- 중복 finding 병합
- severity 계산
- confidence 보정
- evidence 정리
- recommendation 생성

## 3.8 Reporter

출력:

- Markdown report
- JSON findings
- metrics summary

## 4. 데이터 흐름

## 4.1 분석 흐름

```text
1. trace 파일 입력
2. adapter 선택
3. SimpleAgentRun 생성
4. metric 계산
5. rule checker 실행
6. LLM judge 실행
7. finding 병합
8. score 계산
9. report 생성
```

## 4.2 CI 흐름

```text
Pull Request
  -> test agent run
  -> LangSmith/JSONL trace export
  -> judge-agent-simple analyze
  -> findings.json/report.md 생성
  -> score 기준 pass/warning/block
```

## 5. SimpleAgentRun

```json
{
  "run_id": "r1",
  "framework": "langgraph",
  "agent_name": "research-agent",
  "user_input": "...",
  "instructions": {},
  "events": [],
  "final_output": "...",
  "metadata": {}
}
```

## 6. Event Types

초기 event type:

- `llm_call`
- `tool_call`
- `tool_result`
- `retrieval`
- `memory`
- `graph_node`
- `graph_edge`
- `error`
- `final_output`

## 7. Finding 출력

```json
{
  "id": "JD-001",
  "category": "tool",
  "metric": "tool_argument_correctness",
  "severity": "high",
  "confidence": 0.9,
  "evidence": ["tool call search used query not grounded in user input"],
  "expected": "Tool argument should be derived from user input or state",
  "actual": "Agent generated unrelated query",
  "recommendation": "Add argument grounding validation"
}
```

## 8. Scoring

- 100점 시작
- Critical: -30
- High: -15
- Medium: -7
- Low: -2

Gate:

- `pass`: 85점 이상, High/Critical 없음
- `warning`: 70점 이상, Critical 없음
- `block`: 70점 미만 또는 Critical 존재

## 9. 저장 구조

```text
simple-runs/
  traces/
  normalized/
  findings/
  reports/
  baselines/
```

## 10. CLI

```bash
judge-agent-simple analyze \
  --trace ./traces/run.json \
  --framework langgraph \
  --output ./reports/report.md \
  --json ./reports/findings.json
```

```bash
judge-agent-simple compare \
  --baseline ./baselines/main.json \
  --current ./reports/findings.json
```

## 11. 구현 우선순위

### Phase 1

- schema
- trace reader
- markdown/json reporter

### Phase 2

- LangSmithAdapter
- LangChain/LangGraph JSONL adapter

### Phase 3

- rule checkers
- basic metrics

### Phase 4

- LLM judges
- baseline compare
- CI gate

## 12. 보안/프라이버시

- prompt/context raw text는 opt-in
- secret/token/key 자동 마스킹
- state는 allowlist field만 저장
- report에는 최소 evidence excerpt만 포함

## 13. 결론

Simple 버전은 모든 agent framework를 지원하지 않는다. LangChain/LangGraph trace를 정확히 수집하고, tool/context/graph flow drift를 빠르게 찾는 데 집중한다.

## 11. 대상 Agent 기준: LangGraph ReAct Agent

Simple Judge Agent의 1차 target은 다음 구성을 가진 LangChain/LangGraph agent다.

```text
LangGraph StateGraph
  nodes:
    initialize_agent
    react_agent
    validate_findings
    finalize

react_agent:
  LLM Thought
  -> Action: tool / retriever / MCP
  -> Observation
  -> repeat
  -> finish
```

필수 관찰 대상:

- LLM: prompt, model, input/output, usage, error
- Prompt: system prompt, ReAct protocol, tool policy, output contract
- Tools: name, args, result, error, source state
- RAG: query, retrieved documents, relevance, context usage
- MCP: server, method, args, result, service metadata usage
- State: node별 state snapshot, selected graph edge
- Final output: evidence/metric/context groundedness

## 12. ReAct Drift 분석 관점

Judge Agent는 단순히 최종 답변만 보지 않고 ReAct trajectory를 분석한다.

| 분석 축 | 정상 | Drift |
|---|---|---|
| Thought→Action alignment | 필요한 tool을 순서대로 선택 | 근거 없이 finish |
| Action argument grounding | user input/state에서 파생 | unrelated endpoint/query |
| Observation usage | tool result가 다음 thought/report에 반영 | observation 무시 |
| RAG usage | runbook은 context/hypothesis로 사용 | runbook을 확정 원인으로 단정 |
| MCP usage | service metadata로 routing/context 보강 | 잘못된 service owner/SLO 사용 |
| Validation | metric/evidence/context contract 검증 | 검증 skip 또는 false pass |

## 13. 확장 Event Types

기존 event type에 다음을 추가한다.

- `agent_components`
- `instruction_snapshot`
- `react_step`
- `observation`
- `mcp_start`
- `mcp_end`
- `mcp_error`
- `validation_result`

Normalizer는 LangSmith/LangChain trace에서도 위 canonical event로 변환해야 한다.
