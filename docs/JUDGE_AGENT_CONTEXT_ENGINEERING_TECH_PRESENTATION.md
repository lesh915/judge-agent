# 기술 발표 자료: Judge Agent를 위한 Context Engineering, LangGraph 설계, Drift Telemetry

작성일: 2026-05-15  
위치: `docs/JUDGE_AGENT_CONTEXT_ENGINEERING_TECH_PRESENTATION.md`  
대상 문서:

1. `docs/context-engineering-guide.md`
2. `docs/langchain-langgraph-context-engineering-guide.md`
3. `docs/DRIFT_TELEMETRY_INTEGRATION_GUIDE.md`

---

## 발표 목적

이 발표 문서는 `docs/` 폴더의 세 문서를 기반으로, **AI Agent를 운영 가능한 수준으로 만들기 위한 Context Engineering 방법론**, **LangChain/LangGraph 기반 에이전트 구현 전략**, 그리고 **Judge Agent가 Drift를 탐지하기 위해 필요한 Telemetry 수집 체계**를 하나의 기술 발표 흐름으로 재구성한 자료다.

발표자는 이 문서를 기반으로 슬라이드를 제작하거나, 본 문서 자체를 발표 원고로 사용할 수 있다.

---

## 전체 발표 구성

- Part 1. 문제 정의: 왜 Context Engineering과 Drift Telemetry가 필요한가
- Part 2. Context Engineering 기본 개념과 방법론
- Part 3. LangChain/LangGraph 에이전트의 Context Engineering
- Part 4. Drift Telemetry 수집/전송 구조
- Part 5. Judge Agent 관점의 평가·탐지·운영 아키텍처
- Part 6. 구현 체크리스트와 로드맵

---

# Slide 1. Title

## Judge Agent를 위한 Context Engineering & Drift Telemetry

**운영 가능한 AI Agent를 만들기 위한 컨텍스트 설계, LangGraph 구조화, Drift 관측 체계**

발표 키워드:

- Context Engineering
- LangChain / LangGraph
- ReAct Agent
- RAG / Memory / Tool Use
- Drift Telemetry
- Judge Agent
- Observability

### 발표자 노트

오늘 발표의 핵심은 “좋은 모델을 쓰면 에이전트가 안정적으로 동작한다”는 가정을 깨는 것이다. 실제 운영 환경에서 AI Agent의 신뢰성은 모델 성능뿐 아니라, 모델이 어떤 컨텍스트를 보고 판단하는지, 어떤 도구를 어떤 순서로 사용하는지, 그리고 그 과정이 얼마나 잘 관측되는지에 의해 결정된다.

---

# Slide 2. 발표의 핵심 질문

## 우리가 해결하려는 문제

1. AI Agent가 왜 시간이 지나며 목표에서 벗어나는가?
2. 왜 더 긴 컨텍스트 창이 항상 더 나은 답을 만들지 않는가?
3. LangGraph 에이전트에서 컨텍스트는 어디에 존재하는가?
4. Judge Agent는 어떤 데이터를 보고 drift를 판단해야 하는가?
5. 운영 가능한 에이전트를 만들려면 어떤 telemetry가 필요한가?

### 발표자 노트

세 문서는 각각 다른 층위를 다룬다. 첫 번째 문서는 Context Engineering의 일반 이론, 두 번째 문서는 LangChain/LangGraph 구현 관점, 세 번째 문서는 drift 탐지를 위한 데이터 수집 관점이다. 오늘 발표는 이 세 층위를 하나로 연결한다.

---

# Slide 3. 세 문서의 역할

## 발표의 원천 문서

| 문서 | 핵심 역할 |
|---|---|
| `context-engineering-guide.md` | Context Engineering의 개념, 절차, 방법론, 실패 모드, 오픈소스, 실무 예시 |
| `langchain-langgraph-context-engineering-guide.md` | LangChain/LangGraph 에이전트에서 State, Node, Edge, Tool, RAG, Memory를 어떻게 설계할지 |
| `DRIFT_TELEMETRY_INTEGRATION_GUIDE.md` | reference agent가 drift 탐지용 데이터를 어디서 생성하고, 어떻게 trace로 기록하는지 |

### 발표자 노트

이 세 문서를 합치면 “에이전트 설계 → 실행 → 관측 → 평가 → 개선”의 전체 루프가 된다. Context Engineering은 설계 원칙이고, LangGraph는 구현 구조이며, Drift Telemetry는 운영과 평가를 위한 데이터 계층이다.

---

# Slide 4. 한 장 요약

## 운영 가능한 AI Agent의 3요소

```text
Context Engineering
  모델이 무엇을 보고 판단하는가?

LangGraph Architecture
  그 컨텍스트가 어떤 상태와 노드 흐름으로 관리되는가?

Drift Telemetry
  실행 과정에서 무엇이 기록되고, Judge Agent가 무엇을 검증하는가?
```

### 핵심 메시지

> Prompt는 모델에게 하는 말이고, Context는 모델이 일하는 세계다. Telemetry는 그 세계에서 실제로 무슨 일이 일어났는지 남기는 증거다.

---

# Slide 5. AI Agent 운영의 현실

## 데모와 운영의 차이

데모에서는 다음이 잘 동작한다.

- 짧은 입력
- 명확한 목표
- 제한된 도구
- 단발성 응답
- 작은 문서 검색

운영에서는 다음이 발생한다.

- 긴 대화와 누적 상태
- 여러 도구 호출
- RAG 문서 충돌
- 오래된 메모리
- 사용자 목표 변경
- 실패한 tool call
- 부분적으로 잘못된 중간 추론
- 외부 시스템 side effect

### 발표자 노트

AI Agent는 단순히 LLM 호출을 반복하는 시스템이 아니다. 상태가 누적되고, 도구 결과가 들어오고, 이전 판단이 다음 판단에 영향을 준다. 그래서 운영 환경에서는 context 관리와 trace 수집이 필수다.

---

# Slide 6. 문제: Agent Drift

## Drift란 무엇인가

Agent Drift는 에이전트가 원래 의도, 지시, 목표, 근거, 절차에서 벗어나는 현상이다.

주요 유형:

- **Goal Drift**: 원래 목표에서 벗어남
- **Tool Drift**: 잘못된 도구를 선택하거나 불필요하게 반복 호출
- **Memory Drift**: 관련 없는 기억 또는 오래된 기억 사용
- **RAG Drift**: 검색 문서를 잘못 해석하거나 과도하게 일반화
- **Evidence Drift**: 근거 없이 수치나 원인을 주장
- **Handoff Drift**: 노드/에이전트 간 전달 과정에서 의미가 변형
- **Context Bloat**: 불필요한 컨텍스트가 과도하게 누적
- **Context Poisoning**: 잘못된 정보가 state나 memory에 들어가 이후 판단을 오염

---

# Slide 7. Context Engineering의 정의

## 단순 Prompt Engineering을 넘어

Context Engineering은 다음을 설계·운영하는 discipline이다.

> LLM/Agent가 목표를 달성하기 위해 필요한 정보를 외부 세계에서 가져오고, 장기/단기 기억에 저장하고, 현재 작업에 맞게 선택하고, 중복·충돌·노이즈를 줄이고, 안전하고 검증 가능한 형태로 모델에게 제공하는 전체 시스템.

### Prompt Engineering과의 차이

| 구분 | Prompt Engineering | Context Engineering |
|---|---|---|
| 질문 | 어떻게 말할까? | 무엇을 보여줄까? |
| 범위 | 지시문, 예시 | 지시문 + 검색 + 메모리 + 도구 + 상태 + 검증 |
| 단위 | prompt | 정보 파이프라인 |
| 실패 원인 | 지시 모호함 | 정보 누락/과다/충돌/오염 |

---

# Slide 8. LLM의 Context Window는 작업 메모리다

## 모델이 실제로 보는 것

LLM은 다음 컨텍스트를 기반으로 응답한다.

- System / Developer / User instructions
- 이전 대화 기록
- RAG로 검색된 문서
- 도구 목록과 도구 설명
- 도구 호출 결과
- 메모리에서 선택된 사용자/프로젝트 정보
- few-shot 예시
- 출력 형식 스키마
- 안전 정책과 비즈니스 규칙
- 현재 workflow state

### 발표자 노트

중요한 것은 모델이 “학습 데이터 전체”를 자유롭게 검색하는 것이 아니라, 현재 context window에 들어온 정보를 중심으로 다음 토큰을 생성한다는 점이다. 따라서 context window는 CPU의 RAM처럼 관리해야 한다.

---

# Slide 9. 더 긴 컨텍스트가 항상 답은 아니다

## Long Context Failure Modes

긴 컨텍스트는 다음 문제를 만든다.

1. **Context Poisoning**  
   잘못된 정보가 컨텍스트에 들어가 이후 판단을 오염

2. **Context Distraction**  
   너무 많은 과거 정보가 현재 작업 판단을 방해

3. **Context Confusion**  
   불필요한 문서·도구·지시가 모델을 혼란스럽게 함

4. **Context Clash**  
   컨텍스트 내부 정보들이 서로 충돌

5. **Lost-in-the-middle**  
   긴 컨텍스트 중간의 핵심 정보를 놓침

### 발표자 노트

컨텍스트 창이 커졌다고 해서 모든 문서, 모든 로그, 모든 도구를 넣어도 된다는 뜻은 아니다. 운영 에이전트의 핵심은 “많이 넣기”가 아니라 “필요한 것을 정확히 넣기”다.

---

# Slide 10. Context Engineering의 4대 전략

## Write / Select / Compress / Isolate

| 전략 | 의미 | 실무 예시 |
|---|---|---|
| Write | 컨텍스트를 외부에 기록 | scratchpad, memory, checkpoint, artifact |
| Select | 필요한 컨텍스트만 선택 | RAG, memory retrieval, tool selection |
| Compress | 핵심만 남기고 압축 | summary, error compaction, tool output summary |
| Isolate | 컨텍스트를 역할/작업별 격리 | subgraph, subagent, tool permission scope |

### 발표자 노트

LangChain이 제시한 Write/Select/Compress/Isolate는 실제 LangGraph 설계와 매우 잘 맞는다. LangGraph의 state는 Write, node별 projection은 Select, observation summary는 Compress, subgraph와 tool scope는 Isolate다.

---

# Slide 11. Context 구성 요소

## 컨텍스트는 하나가 아니다

1. **Instruction Context**  
   역할, 정책, 금지사항, 출력 형식

2. **User / Task Context**  
   현재 요청, 목표, 제약, 성공 기준

3. **Knowledge Context**  
   문서, DB, 웹 검색, 코드베이스

4. **Memory Context**  
   사용자 선호, 과거 결정, 절차

5. **Tool Context**  
   도구 이름, 설명, schema, 권한

6. **State Context**  
   workflow 단계, 중간 결과, 오류, 검증 상태

7. **Output Contract Context**  
   JSON schema, markdown 구조, report format

---

# Slide 12. Context Engineering 표준 절차

## 설계 순서

```text
1. 목표와 성공 기준 정의
2. Context inventory 작성
3. Always / Relevant / Never include 분류
4. Query understanding / augmentation 설계
5. Retrieval 설계
6. Context packing 설계
7. Tool use 정책 설계
8. Memory 정책 설계
9. Compression 정책 설계
10. Evaluation 설계
11. Observability 설계
```

### 발표자 노트

Context Engineering은 prompt 작성 단계에서 시작하는 것이 아니라, 정보 자산 목록화와 권한/선택/압축 정책 정의에서 시작한다. 마지막에는 반드시 evaluation과 observability가 붙어야 한다.

---

# Slide 13. Context Inventory 예시

## 어떤 정보를 모델에게 줄 수 있는가

| 컨텍스트 | 저장 위치 | 주입 방식 | 위험 |
|---|---|---|---|
| 정책 문서 | docs / DB | RAG | 오래된 버전 사용 |
| 사용자 요청 | input | direct | 모호한 의도 |
| 로그 파일 | file / object store | tool summary | raw log 과다 주입 |
| 실행 상태 | graph state | projection | 전체 state 노출 |
| 도구 목록 | tool registry | dynamic select | tool confusion |
| 메모리 | store | relevance retrieval | memory overreach |
| 검증 결과 | validator | final gate | 누락 시 hallucination |

---

# Slide 14. Context Packing 원칙

## 모델에게 전달하는 순서도 설계 대상이다

권장 순서:

```text
1. Core instruction / role
2. Safety and priority rules
3. Task objective and success criteria
4. Output schema
5. Relevant state
6. Selected memories
7. Retrieved knowledge with citations
8. Available tools
9. User request
```

중요 원칙:

- 출처별 구분자를 명확히 한다.
- 오래된 정보와 최신 정보를 구분한다.
- 충돌 정보는 숨기지 않고 명시한다.
- 모델이 필요 없는 raw data는 넣지 않는다.

---

# Slide 15. 대표 아키텍처 패턴

## Context Engineering 관점의 AI Agent 구조

1. **Simple Augmented LLM**  
   prompt + examples + single LLM call

2. **RAG Pipeline**  
   query rewrite → retrieval → rerank → context pack → answer

3. **Agent with Tools**  
   LLM decision loop + tool call + observation

4. **Workflow + LLM Steps**  
   deterministic flow 안에 LLM step 배치

5. **Multi-Agent / Subgraph Isolation**  
   역할별 context window 분리

### 발표자 노트

운영 환경에서는 무조건 agent loop를 만드는 것보다, 예측 가능한 절차는 workflow로 고정하고 동적 판단이 필요한 곳만 LLM에게 맡기는 구조가 안정적이다.

---

# Slide 16. LangGraph로 넘어가기

## 왜 LangGraph인가

LangGraph는 agent workflow를 graph로 모델링한다.

핵심 구성:

- **State**: 현재 애플리케이션 snapshot
- **Node**: state를 읽고 작업을 수행한 뒤 update 반환
- **Edge**: 다음 node를 결정
- **Checkpointer**: state snapshot 저장
- **Store**: long-term memory 저장

Context Engineering 관점에서 LangGraph의 장점:

- 컨텍스트를 state channel로 분리 가능
- node별로 필요한 컨텍스트만 전달 가능
- checkpoint로 오염 지점 추적 가능
- subgraph로 context isolation 가능
- validation node로 final gate 구성 가능

---

# Slide 17. LangGraph의 State는 컨텍스트 저장소다

## State ≠ LLM Prompt

LangGraph State는 모델에게 매번 전부 보여주는 텍스트가 아니라, **컨텍스트 후보를 구조화해 보관하는 저장소**다.

예시:

```text
request          사용자 요청/목표
rawLogs          원본 로그 참조
parsedRecords    구조화된 로그
metrics          결정적 계산 결과
anomalies        이상 탐지 결과
evidence         최종 주장 근거
ragContext       검색된 runbook 문서
mcpContext       서비스 메타데이터
reactSteps       행동 경로 요약
validation       검증 결과
errors           오류 요약
finalReport      최종 산출물
```

### 발표자 노트

좋은 state 설계는 raw data, evidence, retrieval context, metadata, validation을 분리한다. 이 분리가 되어야 Judge Agent가 어떤 근거로 어떤 판단이 나왔는지 검증할 수 있다.

---

# Slide 18. 나쁜 State 설계 vs 좋은 State 설계

## 나쁜 설계

```python
class State(TypedDict):
    messages: list
    everything: dict
```

문제:

- 어떤 node가 무엇을 읽고 쓰는지 불명확
- 전체 state가 LLM에 주입됨
- context bloat 발생
- 검증 어려움

## 좋은 설계

```python
class AgentState(TypedDict):
    request: RequestContext
    evidence: EvidenceState
    retrieved_context: list[RetrievedChunk]
    tool_observations: list[ToolObservationSummary]
    validation: ValidationState
    errors: list[ErrorSummary]
    final: FinalOutput | None
```

---

# Slide 19. Input / Internal / Output Schema 분리

## 외부 인터페이스와 내부 컨텍스트를 분리하라

```python
class InputState(TypedDict):
    user_input: str
    access_log_path: str

class InternalState(TypedDict):
    request: dict
    raw_log_ref: str | None
    metrics: dict
    rag_context: list[dict]
    mcp_context: dict
    validation: dict
    final_report: str | None

class OutputState(TypedDict):
    final_report: str
    validation_passed: bool
```

장점:

- 내부 raw context가 외부 출력으로 새지 않는다.
- graph 내부 state와 public contract를 분리한다.
- 운영·보안·테스트가 쉬워진다.

---

# Slide 20. Node는 Context Boundary다

## 각 Node는 읽고 쓰는 컨텍스트가 명확해야 한다

Node contract 예:

```yaml
node: compute_log_metrics
reads:
  - filteredRecords
writes:
  - metrics
llm_visible_output:
  - request_count
  - error_rate
  - latency_percentiles
hidden_raw_output:
  - none
failure_policy:
  - filteredRecords가 비어 있으면 warning 반환
context_risks:
  - LLM이 metric을 추측하면 안 됨
```

### 발표자 노트

LangGraph에서 node는 단순 함수지만, Context Engineering에서는 중요한 경계다. 이 node가 어떤 context를 읽고, 어떤 state를 갱신하며, 어떤 정보를 LLM에게 노출할지 명확해야 한다.

---

# Slide 21. Deterministic Node와 LLM Node 분리

## LLM에게 모든 것을 맡기지 않는다

Deterministic node:

- parse request
- read file
- parse access log
- filter records
- compute metrics
- detect anomalies
- validate schema
- redact PII

LLM node:

- 모호한 의도 해석
- 다음 action 선택
- hypothesis generation
- 최종 보고서 작성

### 핵심 원칙

> 숫자와 검증은 코드로, 설명과 판단은 LLM으로.

---

# Slide 22. Edge는 Context Flow Control이다

## 다음에 어떤 컨텍스트를 수집할지 결정

Conditional edge 예:

```python
def route_after_metrics(state):
    if not state["metrics"]:
        return "compute_metrics"
    if state["metrics"].get("error_rate", 0) > 0.05:
        return "retrieve_runbook"
    return "finalize"
```

효과:

- 불필요한 RAG 호출 감소
- 정보 부족 상태에서 finalize 방지
- context flow를 코드로 통제
- LLM의 자율성을 안전하게 제한

---

# Slide 23. Tool Description도 컨텍스트다

## 도구가 많을수록 혼란이 커진다

나쁜 tool description:

```text
analyze: analyze many things and find problems
```

좋은 tool description:

```text
compute_log_metrics:
Compute request count, error count, error rate, and latency percentiles from already-filtered web access log records. Use for quantitative metric claims.
```

Context Engineering 포인트:

- 도구 이름은 구체적으로 작성
- schema는 엄격하게 정의
- 현재 state에서 필요한 도구만 노출
- side-effect 도구는 승인 전 숨김

---

# Slide 24. Dynamic Tool Selection

## 모든 도구를 항상 보여주지 않는다

```python
def select_tools(state):
    if not state.request.get("targetPath"):
        return ["parse_user_request"]
    if state.rawLogs is None:
        return ["read_log_file"]
    if not state.parsedRecords:
        return ["parse_access_log"]
    if not state.filteredRecords:
        return ["filter_log_records"]
    if not state.metrics:
        return ["compute_log_metrics"]
    if not state.ragContext:
        return ["retrieve_runbook"]
    if not state.mcpContext:
        return ["get_service_context"]
    return ["finish"]
```

### 발표자 노트

Tool drift는 tool list가 너무 넓을 때 자주 발생한다. 가장 강력한 해결책은 prompt로 “도구를 잘 골라라”라고 말하는 것이 아니라, 애초에 현재 단계에서 필요한 도구만 보여주는 것이다.

---

# Slide 25. Tool Output Compression

## Raw output과 LLM-facing summary 분리

원본 tool output:

```json
{
  "records": [10000개의 로그 record],
  "parse_error_count": 2,
  "total_lines": 10000
}
```

LLM에 보여줄 summary:

```json
{
  "record_count": 9998,
  "parse_error_count": 2,
  "parse_error_rate": 0.0002,
  "raw_record_ref": "artifact://run-123/parsed-records"
}
```

효과:

- context bloat 감소
- 민감 정보 노출 감소
- Judge Agent가 raw reference를 따라 검증 가능

---

# Slide 26. RAG는 하나의 Node가 아니라 Pipeline이다

## LangGraph RAG 설계

```text
query_understanding
  → retrieve_candidates
  → rerank_context
  → compress_context
  → validate_context
  → answer_or_next_tool
```

RAG context 설계 원칙:

- `doc_id`, `source`, `score`, `excerpt` 유지
- 권한과 최신성 필터 적용
- RAG 문서의 역할 구분
- measured evidence와 retrieved guidance 분리

### RAG context 역할 구분

| 유형 | 역할 |
|---|---|
| 정책 문서 | authoritative source |
| runbook | operational guidance |
| 과거 incident | episodic reference |
| 외부 블로그 | background knowledge |

---

# Slide 27. Memory 설계

## Short-term vs Long-term

LangGraph memory는 크게 두 가지다.

1. **Short-term memory**
   - thread-scoped memory
   - graph state와 checkpoint로 유지
   - 현재 대화/작업의 진행 상태

2. **Long-term memory**
   - thread를 넘어 유지
   - store와 namespace 사용
   - 사용자 선호, 프로젝트 규칙, 과거 결정

Memory policy:

```yaml
max_items: 5
min_relevance: 0.75
prefer:
  - explicit user statements
  - recent validated facts
exclude:
  - stale hypotheses
  - memories without source
  - sensitive data unless required
```

---

# Slide 28. Checkpoint와 Persistence

## Checkpoint는 되돌릴 수 있는 Context History다

LangGraph checkpointer는 각 step의 state snapshot을 thread별로 저장한다.

가능해지는 것:

- human-in-the-loop approval
- conversational memory
- time travel debugging
- fault-tolerant execution
- context poisoning 지점 추적

예:

```python
config = {"configurable": {"thread_id": "incident-001"}}
graph.invoke(input_state, config=config)
```

### 발표자 노트

운영 에이전트에서 checkpoint는 단순 저장 기능이 아니다. “어느 순간 컨텍스트가 망가졌는가”를 역추적할 수 있는 핵심 관측 지점이다.

---

# Slide 29. ReAct 에이전트의 위험

## ReAct는 강력하지만 drift가 쉽다

주요 문제:

- Thought가 길어져 context bloat 발생
- Observation에 raw data 누적
- 이미 호출한 tool 반복
- 충분한 evidence 없이 finish
- RAG 문서를 측정 근거처럼 사용
- tool error 무시
- tool list 과다로 잘못된 action 선택

해결책:

- step별 context 최소화
- observation summary만 유지
- dynamic tool selection
- max_steps 설정
- finish gate 코드화
- validation node 추가

---

# Slide 30. ReAct Step Context 최소화

## 매 step에 필요한 정보만 제공

```json
{
  "step": 4,
  "goal": "Analyze /api/login 5xx spike from web logs",
  "progress": {
    "request_parsed": true,
    "logs_loaded": true,
    "records_parsed": true,
    "records_filtered": false,
    "metrics_computed": false
  },
  "last_observation": {
    "tool": "parse_access_log",
    "record_count": 10000,
    "parse_error_count": 2
  },
  "available_tools": ["filter_log_records"],
  "constraints": [
    "Do not compute metrics before filtering records",
    "Do not finish before evidence is collected"
  ]
}
```

---

# Slide 31. Finish Gate

## 최종 답변은 조건을 만족해야 한다

```python
def can_finish(state):
    missing = []
    if not state.request.get("targetPath"):
        missing.append("targetPath")
    if not state.metrics:
        missing.append("metrics")
    if not state.evidence.get("logLines"):
        missing.append("evidence")
    if not state.ragContext:
        missing.append("rag_context")
    if not state.mcpContext:
        missing.append("mcp_context")
    return not missing, missing
```

### 핵심

Prompt로 “근거 없이 끝내지 마”라고 말하는 것보다, 코드로 finish를 막는 것이 안정적이다.

---

# Slide 32. Reference Agent 구조

## `reference_agent/weblog_agent`

구성 파일:

```text
graph.py       ReAct loop, node/edge orchestration
state.py       WebLogAnalysisState
prompts.py     system prompt, ReAct protocol, tool policy, output contract
tools.py       deterministic log tools
rag.py         LocalRunbookRetriever
mcp.py         MCP service context client
trace.py       trace logging
validation.py  final validation
```

구성요소:

- LLM
- Prompt
- Tools
- MCP
- RAG
- State
- Trace
- Validation

---

# Slide 33. Reference Agent의 Context Flow

## 실행 흐름

```text
run_start
  → instruction_snapshot
  → initialize_agent
  → react_agent
      → parse_user_request
      → read_log_file
      → parse_access_log
      → filter_log_records
      → compute_log_metrics
      → detect_log_anomalies
      → retrieve_runbook
      → get_service_context
      → collect_evidence
      → finish
  → validate_findings
  → finalize
  → final_output
  → run_end
```

### 발표자 노트

이 흐름은 Context Engineering과 Drift Telemetry가 결합된 좋은 예다. 각 node와 tool call은 state를 갱신하고, 동시에 trace로 기록된다. Judge Agent는 이 trace를 읽어 drift를 판단한다.

---

# Slide 34. WebLogAnalysisState 해석

## Drift 판단에 필요한 상태

```text
request             사용자 요청과 targetPath
logSource           로그 파일과 format
rawLogs             원본 로그 count/truncated
parsedRecords       파싱된 로그
filteredRecords     대상 endpoint/status로 필터링된 로그
metrics             error_rate, latency, count
anomalies           threshold/baseline 기반 이상
ragContext          runbook 검색 결과
mcpContext          owner/SLO/dependency/deployment
reactSteps          action path
evidence            log lines, metric refs
validation          검증 결과
errors              오류
finalReport         최종 보고서
```

핵심:

- evidence와 RAG context가 분리됨
- metric은 tool 결과로 생성됨
- validation이 별도 state로 존재

---

# Slide 35. Drift Telemetry란?

## Agent 실행의 관측 데이터

Drift telemetry는 에이전트가 drift를 일으켰는지 판단하기 위해 필요한 실행 로그다.

수집 대상:

- run/session lifecycle
- prompt/instruction snapshot
- graph node transition
- ReAct thought/action/observation
- tool call input/output/error
- LLM request/response/error/skipped
- MCP request/response/error
- RAG retrieval result
- validation result
- final output

### 핵심

> Judge Agent는 최종 답변만 보면 안 된다. 답변이 만들어진 경로를 봐야 한다.

---

# Slide 36. TraceLogger: Drift Telemetry의 단일 Sink

## 모든 이벤트는 TraceLogger를 통과한다

```python
class TraceLogger:
    def emit(self, event_type: str, **payload):
        event = {
            "type": event_type,
            "run_id": self.run_id,
            "timestamp": ...,
            **payload,
        }
        event = redact(event)
        self._fh.write(json.dumps(event) + "\n")
```

필수 기능:

- run_id 생성
- JSONL trace 저장
- secret/token/password redaction
- node_start / node_end
- tool_start / tool_end / tool_error
- generic emit

---

# Slide 37. Entry Point에서 Trace 생성

## Agent 실행 시작 지점에서 주입

```python
logger = TraceLogger(trace_path, run_id=fixture_id)
agent = WebLogAnalysisAgent(logger, fault=fx.fault, use_llm=use_llm)
state = agent.run(...)
```

다른 에이전트에 이식할 때 권장 패턴:

```python
def run_my_agent(user_input, ...):
    trace = TraceLogger(trace_path, run_id=run_id)
    try:
        agent = MyAgent(trace_logger=trace)
        return agent.run(user_input)
    finally:
        trace.close()
```

### 발표자 노트

telemetry는 나중에 붙이는 부가기능이 아니라 agent 생성 시점부터 주입되어야 한다. 그래야 run_start부터 final_output까지 동일한 run_id로 연결된다.

---

# Slide 38. Run Lifecycle Telemetry

## 실행 단위 식별

필수 이벤트:

- `run_start`
- `run_end`
- `final_output`

`run_start` payload 예:

```json
{
  "type": "run_start",
  "agent_name": "weblog-react-agent",
  "agent_version": "0.3.0",
  "framework": "langgraph",
  "architecture": "react",
  "components": ["llm", "prompt", "tools", "mcp", "rag"],
  "user_input": "...",
  "llm_model": "..."
}
```

Judge Agent 활용:

- agent version별 drift 비교
- framework/architecture별 실패율 분석
- 동일 입력에 대한 regression 확인

---

# Slide 39. Instruction Snapshot

## Prompt Drift 탐지의 핵심

이벤트:

```text
instruction_snapshot
```

기록 대상:

- system prompt
- ReAct protocol
- tool policy
- output contract

탐지 가능한 문제:

- system prompt 변경으로 인한 행동 변화
- tool policy 누락
- output contract 약화
- 안전 지시 제거
- ReAct protocol 위반

### 발표자 노트

에이전트가 왜 갑자기 다른 방식으로 행동하는지 분석하려면, 실행 당시 prompt가 무엇이었는지 반드시 남아 있어야 한다.

---

# Slide 40. Node / Edge Telemetry

## Graph 실행 경로를 기록한다

이벤트:

- `node_start`
- `node_end`
- `edge_selected`

기록 대상:

- node name
- state snapshot before/after
- edge from/to
- edge selection reason

탐지 가능한 drift:

- 필요한 node를 건너뜀
- validation skip
- finalize 조기 진입
- error handler 반복
- 예상과 다른 branch 선택

---

# Slide 41. ReAct Loop Telemetry

## Thought / Action / Observation 경로

이벤트:

```text
react_step
observation
```

기록 예:

```json
{
  "type": "react_step",
  "step": 3,
  "thought": "Need structured log records",
  "action": "parse_access_log",
  "action_input": {"format": "nginx_combined"}
}
```

Judge Agent 활용:

- action sequence가 타당한지 평가
- 같은 tool 반복 호출 탐지
- finish 조건 위반 탐지
- thought와 action 불일치 탐지

---

# Slide 42. Tool Telemetry

## Evidence Drift를 막는 핵심

이벤트:

- `tool_start`
- `tool_end`
- `tool_error`

기록 대상:

- tool name
- arguments
- output summary
- error type/message

중요 원칙:

- raw records/logs는 redaction 또는 summary 처리
- metric claim은 compute tool result와 연결
- tool failure는 final limitation에 반영

Judge Agent 질문:

> 최종 보고서의 수치 주장은 실제 tool output으로부터 나왔는가?

---

# Slide 43. LLM Telemetry

## 모델 호출을 재현 가능하게 만든다

이벤트:

- `llm_start`
- `llm_end`
- `llm_error`
- `llm_skipped`

기록 대상:

- model
- messages 또는 안전한 projection
- response content
- usage
- latency
- error

Drift 분석 포인트:

- LLM이 잘못된 action을 선택했는가?
- fallback policy가 개입했는가?
- token 사용량이 급증했는가?
- 특정 model version에서 drift가 증가했는가?

---

# Slide 44. RAG / MCP Telemetry

## 외부 컨텍스트의 출처 추적

RAG telemetry:

- query
- retrieved documents
- doc_id
- score
- source

MCP telemetry:

- server
- method
- tool name
- arguments
- output
- error

탐지 가능한 문제:

- 관련 없는 runbook 검색
- 낮은 score 문서를 근거로 사용
- MCP owner/SLO 정보 누락
- service metadata와 final report 불일치

---

# Slide 45. Validation Telemetry

## 최종 품질 Gate

이벤트:

```text
validation_result
```

검증 항목 예:

- metrics_present
- anomalies_have_evidence
- rag_context_present
- mcp_context_present
- output_contract

payload:

```json
{
  "passed": false,
  "checks": ["metrics_present", "output_contract"],
  "issues": ["final report missing Evidence section"]
}
```

### 발표자 노트

Validation telemetry는 Judge Agent의 1차 입력이자, 운영 대시보드에서 품질 회귀를 보는 핵심 지표다.

---

# Slide 46. 이벤트별 Drift 탐지 매핑

## 어떤 telemetry가 어떤 drift를 잡는가

| Drift 유형 | 필요한 이벤트 |
|---|---|
| Goal drift | run_start, final_output, validation_result |
| Prompt drift | instruction_snapshot |
| Tool drift | react_step, tool_start/end |
| Evidence drift | tool_end, final_output, validation_result |
| RAG drift | retrieval result, final_output |
| MCP drift | mcp_end, final_output |
| Handoff drift | node_start/end, edge_selected |
| Context bloat | llm_start messages, token usage, state snapshot |
| Context poisoning | checkpoints, node state diff, errors |

---

# Slide 47. 다른 에이전트에 붙일 때 최소 이식 포인트

## 최소 구현

1. TraceLogger 또는 호환 sink 구현
2. run_start / run_end 기록
3. instruction_snapshot 기록
4. LLM call start/end/error 기록
5. tool call start/end/error 기록
6. final_output 기록
7. validation_result 기록
8. redaction 적용

권장 추가:

- node_start / node_end
- edge_selected
- react_step / observation
- RAG retrieval result
- MCP request/response
- context budget
- checkpoint id

---

# Slide 48. Privacy / 보안 주의사항

## Telemetry는 민감 데이터가 될 수 있다

주의 대상:

- API keys
- tokens
- passwords
- secrets
- PII
- raw logs
- customer messages
- internal service metadata

보안 원칙:

- redaction 기본 적용
- raw output은 artifact ref로 대체
- trace 접근 권한 제한
- 외부 collector 전송 시 암호화
- retention 정책 설정
- 민감 field allowlist/denylist 적용

---

# Slide 49. Judge Agent 관점의 평가 루프

## Observe → Judge → Improve

```text
Agent Run
  → TraceLogger JSONL
  → Judge Agent
      → Drift 유형 분류
      → Evidence alignment 검사
      → Context bloat 측정
      → Tool/RAG/Memory 사용 평가
      → Validation issue 생성
  → Developer Feedback
  → Context Policy / Graph / Prompt / Tool 개선
```

핵심:

- Judge Agent는 최종 응답만 평가하지 않는다.
- 실행 경로와 state 변화, tool evidence를 함께 평가한다.
- drift 탐지는 context engineering 개선으로 이어져야 한다.

---

# Slide 50. 통합 아키텍처

## Context Engineering + LangGraph + Telemetry

```text
User Request
  ↓
LangGraph Input State
  ↓
Context Engineering Layer
  - state projection
  - tool selection
  - RAG selection
  - memory selection
  - compression
  ↓
Graph Execution
  - nodes
  - edges
  - tools
  - LLM
  - MCP
  - RAG
  ↓
TraceLogger
  - JSONL events
  - redaction
  - run_id correlation
  ↓
Validation / Judge Agent
  - drift detection
  - evidence check
  - output contract check
  ↓
Final Report + Feedback Loop
```

---

# Slide 51. 구현 로드맵

## 1단계: Trace 표준화

- TraceLogger 인터페이스 고정
- event schema 문서화
- redaction 강화
- JSONL + collector 이중화 준비

## 2단계: Context 구조화

- State schema 정리
- raw/summary 분리
- evidence/hypothesis 분리
- node별 context projection 구현

## 3단계: Drift Judge 강화

- trace 기반 drift rule 구현
- LLM-as-a-Judge 평가 추가
- regression fixture 구성

## 4단계: 운영화

- dashboard
- alert
- prompt/tool/version 비교
- context budget 추적

---

# Slide 52. 실무 체크리스트: Context Engineering

## 설계 체크

- [ ] 목표와 성공 기준이 명확한가?
- [ ] context inventory가 있는가?
- [ ] always/relevant/never include가 분리되었는가?
- [ ] state schema가 구조화되어 있는가?
- [ ] tool output이 raw와 summary로 분리되는가?
- [ ] RAG source와 score가 유지되는가?
- [ ] memory retrieval policy가 있는가?
- [ ] compression trigger가 있는가?
- [ ] validation gate가 있는가?
- [ ] observability trace가 있는가?

---

# Slide 53. 실무 체크리스트: LangGraph

## 구현 체크

- [ ] input/internal/output schema가 분리되어 있는가?
- [ ] node별 read/write contract가 있는가?
- [ ] deterministic node와 LLM node가 분리되어 있는가?
- [ ] conditional edge가 불필요한 context 수집을 막는가?
- [ ] max_steps가 있는가?
- [ ] finish gate가 코드로 강제되는가?
- [ ] checkpointer와 thread_id가 적용되는가?
- [ ] subgraph 또는 tool scope로 isolation이 되는가?
- [ ] validation node가 final output 전에 실행되는가?

---

# Slide 54. 실무 체크리스트: Telemetry

## 관측 체크

- [ ] run_start/run_end/final_output이 있는가?
- [ ] instruction_snapshot이 있는가?
- [ ] node_start/node_end가 있는가?
- [ ] edge_selected reason이 있는가?
- [ ] react_step과 observation이 있는가?
- [ ] tool input/output/error가 있는가?
- [ ] LLM messages/usage/latency가 있는가?
- [ ] RAG query/result가 있는가?
- [ ] MCP call/result가 있는가?
- [ ] validation_result가 있는가?
- [ ] redaction이 적용되는가?

---

# Slide 55. 핵심 Anti-patterns

## 피해야 할 설계

1. 전체 state를 매번 LLM에 넣기
2. messages를 memory로 무한 누적하기
3. 모든 tool을 항상 노출하기
4. RAG 문서를 측정 근거처럼 사용하기
5. validation을 prompt에만 맡기기
6. checkpoint 없이 장기 실행하기
7. final output만 저장하고 중간 경로를 잃어버리기
8. trace에 secret/raw PII를 그대로 남기기
9. tool error를 limitation에 반영하지 않기
10. prompt 변경 이력을 남기지 않기

---

# Slide 56. 발표 전체 요약

## 세 문서의 결론을 하나로 묶으면

1. **Context Engineering**  
   모델이 무엇을 보고 판단할지 설계하는 discipline

2. **LangGraph Architecture**  
   context를 state/node/edge/checkpoint 단위로 통제하는 구현 구조

3. **Drift Telemetry**  
   agent가 실제로 어떤 context와 도구를 사용했는지 기록하는 증거 계층

4. **Judge Agent**  
   trace를 기반으로 drift, evidence alignment, output contract 위반을 평가하는 검증자

### 핵심 문장

> 운영 가능한 AI Agent는 좋은 답을 한 번 생성하는 시스템이 아니라, 왜 그 답이 나왔는지 재현·검증·개선할 수 있는 시스템이다.

---

# Slide 57. Q&A 예상 질문

## Q1. Prompt만 잘 쓰면 안 되나요?

Prompt는 필요하지만 충분하지 않다. 운영 agent는 RAG, memory, tool, state, checkpoint, validation이 함께 작동한다. Drift는 prompt보다 context flow에서 더 자주 발생한다.

## Q2. 모든 trace를 저장하면 비용과 보안 문제가 크지 않나요?

맞다. 그래서 raw data가 아니라 summary와 artifact reference를 저장하고, redaction과 retention 정책을 적용해야 한다.

## Q3. Judge Agent는 rule-based여야 하나요, LLM-based여야 하나요?

둘 다 필요하다. metric 존재 여부, output section 누락 등은 rule-based가 좋고, goal drift나 reasoning consistency는 LLM-as-a-Judge가 유용하다.

## Q4. LangGraph가 꼭 필요한가요?

필수는 아니지만, state/node/edge/checkpoint를 명시적으로 다룰 수 있어 Context Engineering과 Drift Telemetry를 구현하기 좋다.

---

# Slide 58. 참고 자료

## 내부 문서

- `docs/context-engineering-guide.md`
- `docs/langchain-langgraph-context-engineering-guide.md`
- `docs/DRIFT_TELEMETRY_INTEGRATION_GUIDE.md`

## 주요 외부 자료

- LangChain Blog, “Context Engineering for Agents”
- LangGraph Graph API / Persistence / Memory docs
- Anthropic, “Building effective agents”
- Anthropic, “How we built our multi-agent research system”
- Drew Breunig, “How Long Contexts Fail”
- Model Context Protocol documentation
- HumanLayer, “12-Factor Agents”

---

# Appendix A. 발표 압축안: 20분 버전

## 20분 발표 구성

1. Slide 1~4: 발표 개요 — 2분
2. Slide 5~10: Context Engineering 필요성 — 4분
3. Slide 16~24: LangGraph 설계 핵심 — 5분
4. Slide 32~35: Reference Agent 구조 — 3분
5. Slide 36~46: Drift Telemetry — 4분
6. Slide 49~56: 통합 아키텍처와 결론 — 2분

---

# Appendix B. 발표 압축안: 40분 버전

## 40분 발표 구성

1. 문제 정의와 Agent Drift — 5분
2. Context Engineering 기본 개념 — 8분
3. LangGraph Context 설계 — 12분
4. Reference Agent 구조 해설 — 5분
5. Drift Telemetry 수집 구조 — 7분
6. Judge Agent 평가 루프와 Q&A — 3분

---

# Appendix C. 발표 후 액션 아이템

## 바로 실행할 수 있는 개선 항목

1. `reference_agent/weblog_agent`의 LLM call에 context budget trace 추가
2. `state.snapshot()`을 용도별 projection 함수로 분리
3. ReAct step에서 dynamic tool selection 적용
4. finish gate를 코드로 강제
5. RAG context와 measured evidence를 final report schema에서 더 명확히 분리
6. TraceLogger collector payload schema를 별도 JSON schema로 정의
7. Judge Agent drift rule을 이벤트 매핑 기반으로 확장
8. regression fixture에 context bloat / RAG drift / tool drift 케이스 추가

---

# Appendix D. 최종 메시지

## 발표 마무리

AI Agent를 production에 올린다는 것은 LLM 호출 코드를 작성하는 것보다 훨씬 넓은 문제다.

운영 가능한 Agent에는 다음이 필요하다.

- 명확한 context policy
- 구조화된 graph state
- 제한된 tool exposure
- 출처가 보존된 RAG
- 압축 가능한 observation
- checkpoint 기반 복구
- validation gate
- drift telemetry
- Judge Agent 기반 피드백 루프

최종적으로 우리가 만들고자 하는 것은 단순한 챗봇이 아니라, **자신의 실행 과정을 설명하고 검증받을 수 있는 에이전트 시스템**이다.
