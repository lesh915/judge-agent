# Conversational Judge Agent 개발 계획

작성일: 2026-05-15  
대상 경로: `simple/judge_agent_simple`

## 1. 현재 상태 진단

현재 `simple/judge_agent_simple`은 일반적인 대화형 에이전트라기보다, **분석된 drift finding을 대상으로 질의응답하는 deterministic conversational layer**에 가깝다.

현재 구현된 기능:

- `chat` CLI 명령 제공
- session state 저장/복원
- 사용자 turn 기록
- intent keyword 분류
- finding ID / metric / run ID 기반 focus 선택
- summary, gate, evidence, root cause, recommendation 응답 생성
- API key 없이 CI/로컬에서 deterministic하게 동작

현재 부족한 점:

- LLM 기반 자연어 대화 이해 없음
- tool-calling / ReAct loop 없음
- 대화 중 필요한 분석 도구를 직접 선택/실행하지 않음
- trace 로드 이후에는 정적 finding을 설명하는 수준
- LangGraph 기반 stateful conversational workflow가 아님
- 사용자의 임의 질문을 계획, 도구 사용, 증거 수집, 답변으로 연결하지 못함
- 대화 중 추가 trace 분석, 재분석, 비교, drill-down을 agent action으로 수행하지 못함

따라서 목표는 현재 구현을 폐기하는 것이 아니라, deterministic 분석 엔진 위에 **일반적인 대화형 Agent Runtime**을 추가하는 것이다.

---

## 2. 목표 상태

`simple`은 다음 형태로 동작해야 한다.

```text
User Message
  -> Conversation State
  -> Intent / Task Understanding
  -> Planning
  -> Tool Selection
  -> Tool Execution
  -> Evidence Collection
  -> Response Generation
  -> Session Memory Update
```

일반적인 대화형 Judge Agent의 요구사항:

1. 사용자가 자연어로 질문한다.
2. 에이전트가 질문 의도를 이해한다.
3. 필요한 경우 trace 분석, finding 검색, run 비교, metric 계산, evidence 추출 도구를 호출한다.
4. 도구 결과를 바탕으로 근거 있는 답변을 생성한다.
5. 대화 상태와 현재 focus를 유지한다.
6. 후속 질문에서 이전 맥락을 활용한다.
7. 불확실하거나 근거가 부족하면 명시적으로 말한다.
8. CI 환경에서는 deterministic mode로도 동작한다.

---

## 3. 설계 원칙

## 3.1 Deterministic Core + LLM Conversation Layer

기존 detector/analyzer는 유지한다.

- `ReferenceAgentJsonlAdapter`
- `ReferenceWebLogDetector`
- `score_findings`
- `gate_for`
- `AnalysisResult`

LLM은 drift 자체를 임의로 판단하지 않는다. LLM은 다음 역할을 맡는다.

- 사용자 질문 해석
- 어떤 tool을 호출할지 결정
- evidence를 설명 가능한 답변으로 구성
- 후속 질문 맥락 유지

즉, 핵심 판단은 deterministic metric/finding에 두고, 대화 능력만 LLM으로 확장한다.

## 3.2 Tool-first Agent

대화형 Agent는 내부 기능을 tool로 사용해야 한다.

초기 tool 후보:

| Tool | 역할 |
|---|---|
| `load_traces` | trace JSONL/glob을 로드하고 분석 결과 생성 |
| `list_runs` | 현재 session의 run 목록 반환 |
| `summarize_findings` | 전체 finding 요약 |
| `get_finding` | finding ID/metric/run 기준 상세 조회 |
| `get_evidence` | finding의 evidence 추출 |
| `compare_runs` | 여러 run의 score/gate/finding 비교 |
| `explain_gate` | block/warning/pass 원인 설명 |
| `recommend_fix` | finding 기반 수정 방향 제안 |
| `export_report` | markdown/json report 생성 |

## 3.3 LangGraph Optional, Plain Runtime First

단계적으로 진행한다.

- Phase 1: Plain Python agent loop로 구현
- Phase 2: LangGraph dependency가 있을 경우 graph runtime 제공
- Phase 3: LangGraph checkpoint/store 연동

이렇게 하면 기존 CI 안정성을 유지하면서 점진적으로 일반 agent 구조를 도입할 수 있다.

---
## 3.4 Drift Metrics 측정 항목 반영

대화형 Judge Agent 개발 시 측정해야 할 drift metric은 `docs/DRIFT_METRICS.xlsx`를 기준으로 한다. 이 엑셀 파일은 다음 시트를 포함한다.

- `전체 Metric 목록`: LangChain/LangGraph agent drift 측정 후보 전체
- `MVP 우선순위`: 우선 구현할 공통 MVP metric 7개
- `Ref Agent 우선순위`: `reference_agent/weblog_agent` fixture에 이미 대응되는 metric 8개
- `Severity 분류`: metric별 severity 기준

### 3.4.1 MVP 우선 구현 Metric 7개

일반 대화형 에이전트 개발 시 우선적으로 측정/노출해야 할 metric이다.

| 우선순위 | Metric | Category | 측정 방법 | Severity | 개발 반영 방식 |
|---:|---|---|---|---|---|
| 1 | `tool_argument_correctness` | Tool Use | rule(schema + context) | High | tool call arguments가 user input/state/evidence에서 온 값인지 검증 |
| 2 | `tool_error_handling_score` | Tool Use | rule | Critical | tool error 이후 retry/stop/report 여부를 대화 loop에서 검증 |
| 3 | `answer_context_groundedness` | Context / Retrieval | LLM judge | High | 최종 답변의 claim이 retrieved context/evidence에 grounded 되었는지 평가 |
| 4 | `node_sequence_correctness` | LangGraph Flow | rule(expected path) | Critical | graph mode에서 필수 node 순서와 validation path 실행 여부 검증 |
| 5 | `verification_coverage` | Final Output / Completion | rule | High | 완료 전 필요한 검증(read/diff/test/tool result 확인 등) 수행 여부 측정 |
| 6 | `instruction_adherence_score` | Prompt / Instruction | LLM judge + rule | High | system/tool/output policy 준수 여부 평가 |
| 7 | `redundant_tool_call_count` | Tool Use | rule(중복 탐지) | Medium | 동일 목적 tool 반복 호출 횟수 측정 |

### 3.4.2 Reference Agent 우선 Metric 8개

현재 `simple` 구현은 reference weblog agent trace를 우선 분석하므로, 아래 metric은 기존 detector와 호환되도록 계속 유지하고 대화형 agent tool에서도 조회 가능해야 한다.

| 우선순위 | Metric | 개발 반영 방식 |
|---:|---|---|
| 1 | `output_contract_compliance` | final output markdown section/output contract 준수 여부 |
| 2 | `target_endpoint_consistency` | 사용자 요청의 target path와 tool argument/metric path 일치 여부 |
| 3 | `metric_result_consistency` | metric claim이 실제 `compute_log_metrics` 결과에서 왔는지 여부 |
| 4 | `validation_path_coverage` | `validate_findings` node와 `validation_result` event 실행 여부 |
| 5 | `parse_error_handling_score` | 높은 parse error ratio 처리/차단/limitation 반영 여부 |
| 6 | `rag_context_presence_and_usage` | RAG retrieval 및 final report 반영 여부 |
| 7 | `mcp_context_presence_and_usage` | MCP service context 수집 및 report 반영 여부 |
| 8 | `chat_context_grounding` | 후속 대화가 직전 analysis/focus/evidence에 grounded 되었는지 여부 |

### 3.4.3 전체 Metric Registry

대화형 agent는 모든 metric을 hard-coded 문자열로 흩어놓지 않고 registry로 관리해야 한다. 최소 registry schema는 다음과 같다.

```python
class DriftMetricSpec(TypedDict):
    name: str
    category: str
    measurement_method: str
    value_type: str
    description: str
    severity: str
    mvp_priority: int | None
    ref_agent_priority: int | None
```

초기 registry에는 `docs/DRIFT_METRICS.xlsx`의 `전체 Metric 목록`을 반영한다.

| Category | Metrics |
|---|---|
| Prompt / Instruction | `instruction_adherence_score`, `output_format_compliance`, `prompt_template_version_present` |
| Tool Use | `tool_selection_accuracy`, `tool_argument_correctness`, `tool_error_handling_score`, `redundant_tool_call_count`, `tool_result_grounding_score` |
| Context / Retrieval | `retrieval_context_relevance`, `retrieval_context_precision`, `answer_context_groundedness`, `missing_required_context` |
| Memory / State | `memory_claim_supported`, `state_freshness_score`, `state_value_grounding`, `memory_update_correctness` |
| LangGraph Flow | `node_sequence_correctness`, `edge_decision_correctness`, `node_loop_count`, `graph_completion_path_valid`, `required_checkpoint_present` |
| Final Output / Completion | `task_completion_score`, `verification_coverage`, `final_answer_consistency`, `hallucinated_completion_claim` |
| ReAct / RAG / MCP | `react_step_completeness`, `action_grounding_score`, `observation_utilization_score` |

### 3.4.4 Severity 반영 기준

`docs/DRIFT_METRICS.xlsx`의 `Severity 분류`를 개발 기준으로 사용한다.

| Severity | 대표 조건 | 개발상 처리 |
|---|---|---|
| Critical | 승인 없는 외부/파괴적 action, 민감정보 노출, validation skip, hallucinated completion claim | CI block, 대화 응답에서 최우선 경고 |
| High | tool failure 성공 보고, hallucinated tool argument, context와 반대되는 답변 | warning/block 후보, 수정 우선순위 상위 |
| Medium | 일부 요구사항 누락, 중복 tool/node loop, 낮은 groundedness, state update 누락 | review 필요, 개선 권고 |
| Low | 경미한 format 위반, 영향 낮은 observability gap | 참고 정보로 노출 |

### 3.4.5 대화형 Agent에서 Metric을 사용하는 방식

대화형 agent는 metric을 단순 report 항목으로만 쓰지 않고, 다음 기능에 직접 사용해야 한다.

1. **Planning**: 사용자 질문이 “왜 실패했나?”이면 `gate`, `severity`, MVP priority 기준으로 먼저 조회한다.
2. **Tool Selection**: `metric_name`과 category를 기준으로 `get_finding`, `get_evidence`, `compare_runs`, `recommend_fix` tool을 선택한다.
3. **Answer Grounding**: 답변은 finding evidence, metric spec, severity 기준을 함께 인용한다.
4. **Follow-up Focus**: 사용자가 “그 근거는?”이라고 물으면 직전 metric/finding focus를 유지한다.
5. **CI Gate**: Critical/High metric은 `--fail-on` threshold와 연결한다.
6. **Regression Tracking**: 동일 metric의 score/finding count를 run 간 비교한다.

### 3.4.6 개발 산출물

Metric 반영을 위해 다음 파일을 추가/수정한다.

```text
judge_agent_simple/
  metrics.py             # DriftMetricSpec registry
  tools.py               # metric-aware analysis tools
  conversation_state.py  # focused_metric / metric_history 저장
  conversation_agent.py  # metric 기반 planning/follow-up
  reporter.py            # metric registry metadata 포함
  tests/
    test_metrics.py
    test_conversation_metrics.py
```

완료 기준:

- `docs/DRIFT_METRICS.xlsx`의 MVP 7개와 Ref Agent 8개가 registry에 존재해야 한다.
- 기존 detector finding의 `metric` 값이 registry에 매핑되어야 한다.
- chat에서 “어떤 metric 때문에 block이야?”, “MVP 우선순위 기준으로 먼저 고칠 것 알려줘”, “tool_argument_correctness 근거 보여줘” 같은 질문에 답해야 한다.
- report에는 metric category, severity, priority가 포함되어야 한다.

---

## 4. 제안 아키텍처

```text
judge_agent_simple/
  chat_agent.py          # 기존 deterministic responder 유지
  conversation_agent.py  # 신규: 일반 대화형 agent runtime
  conversation_state.py  # 신규: agent state schema
  tools.py               # 신규: analysis tools registry
  llm.py                 # 신규: LLM provider abstraction
  planner.py             # 신규: intent/task planning
  prompts.py             # 신규: system prompt / tool policy / answer contract
  graph.py               # 신규: optional LangGraph workflow
```

## 4.1 Conversation State

예상 state:

```python
class ConversationState(TypedDict):
    session_id: str
    messages: list[dict]
    loaded_traces: list[str]
    analysis_results: list[dict]
    focus: dict
    pending_question: str | None
    plan: list[dict]
    tool_calls: list[dict]
    evidence: list[dict]
    final_response: str | None
```

## 4.2 Agent Loop

```text
receive user input
  -> append message
  -> classify task
  -> build available tool list
  -> LLM or deterministic planner chooses action
  -> execute tool
  -> update evidence/focus
  -> repeat until answer-ready
  -> generate grounded answer
  -> save session
```

## 4.3 Modes

| Mode | 설명 |
|---|---|
| `deterministic` | 현재 방식. LLM 없이 keyword/rule 기반 응답 |
| `llm` | LLM이 planner/response generator 역할 수행 |
| `hybrid` | deterministic tool results + LLM response synthesis |
| `graph` | LangGraph 기반 stateful workflow |

CLI 예시:

```bash
python3 -m simple.judge_agent_simple.cli chat \
  --traces 'artifacts/weblog-reference/*.jsonl' \
  --session-id weblog-review \
  --mode hybrid
```

---

## 5. 단계별 개발 계획

## Phase 0. 현재 구현 보존 및 명확화

목표:

- 현재 `JudgeChatAgent`를 deterministic chat layer로 명확히 정의
- 일반 대화형 agent와 역할 분리

작업:

- README에 현재 구현 한계 명시
- `JudgeChatAgent` docstring 보강
- `chat --mode deterministic` 옵션 추가 준비

완료 기준:

- 기존 테스트 모두 통과
- 기존 CLI 호환성 유지

## Phase 1. Tool Registry 도입

상태: **1차 구현 완료** (`metrics.py`, `tools.py`, `deterministic-v2`에서 사용)

목표:

- 기존 analyzer/detector/reporter 기능을 agent tool로 감싼다.

작업:

- `metrics.py` 추가: `docs/DRIFT_METRICS.xlsx` 기반 `DriftMetricSpec` registry 정의
- `tools.py` 추가
- 각 tool 입출력 schema 정의
- session state를 받아 동작하는 pure function 형태로 구현
- tool result에 `metric`, `severity`, `priority`, `evidence`, `source`, `confidence` 포함

필수 tools:

- `load_traces`
- `list_runs`
- `summarize_findings`
- `get_finding`
- `get_evidence`
- `explain_gate`
- `recommend_fix`

완료 기준:

- 각 tool 단위 테스트 작성
- MVP 7개 metric과 Ref Agent 8개 metric이 registry에 존재
- 기존 detector finding의 metric 값이 registry와 매핑
- 기존 chat 응답을 tool 기반으로 재구성 가능

## Phase 2. Conversation State / Session 확장

상태: **1차 구현 완료** (`conversation_state.py`, `*.conversation.json` 저장)

목표:

- 일반 agent loop가 사용할 state 구조를 추가한다.

작업:

- `conversation_state.py` 추가
- 기존 `JudgeSessionState`와 호환되도록 migration 함수 제공
- messages, tool_calls, evidence, focus, loaded_traces 저장
- focused_metric, metric_history, severity_filter 저장
- session json versioning 추가

완료 기준:

- 기존 session 파일 로드 가능
- 새 session 파일에 tool_calls/evidence 저장 가능

## Phase 3. Plain Conversational Agent Runtime 구현

상태: **1차 구현 완료** (`conversation_agent.py`, `chat --mode deterministic-v2`)

목표:

- LLM 없이도 작동 가능한 tool-based 대화 loop를 구현한다.

작업:

- `conversation_agent.py` 추가
- deterministic planner 구현
- 질문 유형별 tool chain 정의
  - summary → `summarize_findings`
  - evidence → `get_finding` + `get_evidence`
  - gate → `explain_gate`
  - fix → `recommend_fix`
  - compare → `compare_runs`
- follow-up focus resolution 구현
- metric priority/severity 기반 finding 정렬 구현

완료 기준:

- `왜 block이야?`
- `그 근거는?`
- `어느 run이 제일 위험해?`
- `수정 우선순위 알려줘`
- `JD-001과 JD-002 비교해줘`

위 질문들이 session context를 유지하며 응답해야 한다.

## Phase 4. LLM Provider Abstraction 추가

상태: **1차 구현 완료** (`llm.py`, `prompts.py`, `hybrid` response synthesis)

목표:

- 일반적인 자연어 질문을 처리할 수 있도록 LLM planner/response generator를 선택적으로 추가한다.

작업:

- `llm.py` 추가
- provider interface 정의
- 환경변수 기반 OpenAI/LangChain provider 선택
- API key 없으면 deterministic fallback
- prompt/tool policy 작성

예상 interface:

```python
class LlmClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> LlmResult: ...
```

완료 기준:

- API key 없는 환경에서도 테스트 통과
- API key 있는 환경에서는 hybrid mode로 자연어 질문 처리

## Phase 5. Hybrid Agent Mode

상태: **1차 구현 완료** (`chat --mode hybrid`, deterministic tools + LLM synthesis/fallback)

목표:

- LLM이 질문을 이해하고, deterministic tools로 근거를 가져와, 답변을 생성한다.

작업:

- `--mode hybrid` 추가
- LLM planner prompt 작성
- tool call result를 answer prompt에 주입
- final response contract 적용
- hallucination 방지를 위해 evidence 없는 claim 금지

완료 기준:

- 복합 질문 처리 가능
  - “validation 관련 block 원인과 가장 먼저 고칠 코드를 알려줘”
  - “정상 run과 drift run의 차이를 요약해줘”
  - “이 finding이 실제 운영에서 왜 위험한지 설명해줘”

## Phase 6. Optional LangGraph Runtime

목표:

- LangGraph dependency가 설치된 경우 graph-based conversation workflow를 제공한다.

Graph 제안:

```text
START
  -> load_or_update_context
  -> plan_next_action
  -> execute_tool
  -> evaluate_answer_readiness
      -> execute_tool | generate_response
  -> save_session
  -> END
```

작업:

- `graph.py` 추가
- StateGraph 구성
- checkpoint 옵션 추가
- LangGraph 미설치 시 graceful fallback

완료 기준:

- `pip install -e .[agent]` 환경에서 graph mode 동작
- deterministic/hybrid와 동일한 결과 품질 유지

## Phase 7. 테스트 및 평가

테스트 범위:

- tool unit tests
- conversation state serialization tests
- deterministic planner tests
- CLI chat mode tests
- optional LLM tests는 mock 기반
- LangGraph graph tests는 optional dependency marker 사용

대표 테스트 시나리오:

1. trace 없이 시작하면 trace 로드 요청
2. trace 로드 후 전체 요약
3. block 원인 질문
4. follow-up “근거는?” 질문
5. finding ID 직접 질문
6. run 비교 질문
7. 수정 우선순위 질문
8. session resume 후 focus 유지
9. LLM provider unavailable fallback
10. hallucination 방지: evidence 없는 질문에는 제한 답변

---

## 6. 우선순위

| 우선순위 | 작업 | 이유 |
|---:|---|---|
| P0 | Tool Registry | 일반 agent의 action 기반 구조를 만들기 위한 기반 |
| P0 | Conversation State 확장 | follow-up과 session memory 필수 |
| P1 | Plain Agent Runtime | LLM 없이도 일반 대화형 흐름 확보 |
| P1 | CLI mode 분리 | 기존 기능 보존 + 신규 mode 실험 가능 |
| P2 | LLM Provider | 자연어 이해와 응답 품질 개선 |
| P2 | Hybrid Mode | deterministic evidence + LLM 표현력 결합 |
| P3 | LangGraph Runtime | 제품 방향성과 발표 내용에 맞는 graph 구조화 |

---

## 7. 권장 첫 구현 범위

첫 번째 개발 PR은 너무 크게 만들지 않는다.

### PR 1: Tool Registry + State 확장

상태: **완료**

포함:

- `metrics.py`
- `tools.py`
- `conversation_state.py`
- 기존 `JudgeSessionState`와 호환 가능한 migration path
- unit tests

제외:

- LLM 연동
- LangGraph 연동
- 대규모 CLI 변경

### PR 2: Plain Conversation Agent Runtime

상태: **완료**

포함:

- `conversation_agent.py`
- deterministic planner
- `chat --mode deterministic-v2`
- follow-up focus 유지
- CLI tests

### PR 3: Hybrid LLM Mode

상태: **완료**

포함:

- `llm.py`
- `prompts.py`
- prompt/tool policy
- mock LLM tests
- `chat --mode hybrid`
- metric registry metadata를 LLM response context에 주입
- LLM unavailable fallback

### PR 4: Optional LangGraph Mode

포함:

- `graph.py`
- optional dependency fallback
- graph checkpoint tests

---

## 8. 성공 기준

일반적인 대화형 에이전트로 볼 수 있으려면 다음을 만족해야 한다.

- 사용자가 자유 문장으로 질문해도 agent가 task를 분해한다.
- 필요한 내부 tool을 선택하고 실행한다.
- 결과에 근거/evidence/source를 포함한다.
- 이전 질문의 focus를 유지해 follow-up에 답한다.
- trace 추가 로드, run 비교, finding drill-down이 대화 중 가능하다.
- LLM이 있으면 자연어 처리 품질이 좋아지고, 없어도 deterministic fallback이 가능하다.
- 모든 drift 판단은 tool/detector 결과에 grounding된다.

---

## 9. 결론

현재 `simple`은 대화형 인터페이스를 갖고 있지만, 일반적인 대화형 에이전트라고 부르기에는 아직 부족하다.

다음 개발 방향은 **deterministic 분석 엔진을 유지하면서, tool-calling 기반 conversational runtime을 추가하는 것**이다. 이렇게 하면 CI 안정성과 일반 대화형 사용성을 동시에 확보할 수 있다.
