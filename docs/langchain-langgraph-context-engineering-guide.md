# LangChain/LangGraph 에이전트의 Context Engineering 상세 가이드

작성일: 2026-05-15  
위치: `docs/langchain-langgraph-context-engineering-guide.md`  
관련 문서: `docs/context-engineering-guide.md`

---

## 0. 문서 목적

이 문서는 앞서 작성한 `Context Engineering 상세 가이드`를 바탕으로, **LangChain/LangGraph 방식으로 만든 에이전트**를 Context Engineering 관점에서 별도로 상세히 설명한다.

특히 다음 질문에 답하는 것을 목표로 한다.

1. LangChain/LangGraph 에이전트에서 “컨텍스트”는 구체적으로 어디에 존재하는가?
2. LangGraph의 `State`, `Node`, `Edge`, `Checkpointer`, `Store`, `Tool`, `Retriever`, `Prompt`, `Trace`는 Context Engineering 관점에서 어떤 역할을 하는가?
3. ReAct 에이전트, Tool-calling 에이전트, RAG 에이전트, Multi-step workflow 에이전트를 어떻게 설계해야 컨텍스트 오염과 드리프트를 줄일 수 있는가?
4. `judge-agent` 저장소의 `reference_agent/weblog_agent` 같은 LangGraph/LangChain-style 에이전트를 어떻게 관찰·평가·개선할 수 있는가?
5. 실제 구현 시 사용할 수 있는 state schema, graph pattern, memory policy, retrieval policy, compression policy, observability schema는 무엇인가?

---

## 1. 한 줄 요약

LangChain/LangGraph 에이전트에서 Context Engineering은 단순히 prompt를 잘 쓰는 일이 아니라, **Graph State를 중심으로 Prompt, Messages, Tools, RAG, Memory, MCP, Checkpoints, Traces, Validation을 연결하고, 각 Node가 LLM에게 전달하는 컨텍스트를 의도적으로 통제하는 일**이다.

LangGraph에서는 에이전트가 “대화 하나”가 아니라 **상태가 변하는 그래프 프로그램**이다. 따라서 Context Engineering의 핵심 단위도 prompt 하나가 아니라 다음 전체가 된다.

```text
Graph Input
  → State
  → Node별 Context Builder
  → LLM/Tool/Retriever 호출
  → Observation
  → State Update
  → Edge Routing
  → Checkpoint
  → Final Output
```

---

## 2. LangChain/LangGraph 방식에서 컨텍스트가 존재하는 위치

일반적인 LLM 앱에서는 컨텍스트가 “prompt 안에 들어가는 텍스트”로 보이지만, LangGraph 에이전트에서는 컨텍스트가 여러 계층에 흩어져 있다.

## 2.1 Prompt Context

모델에게 직접 전달되는 instruction이다.

예:

- system prompt
- developer prompt
- ReAct protocol
- tool policy
- output contract
- few-shot examples

`judge-agent`의 reference agent에서는 다음 파일이 여기에 해당한다.

```text
reference_agent/weblog_agent/prompts.py
```

주요 구성:

- `SYSTEM_PROMPT`: 에이전트 역할, 구성요소, 금지사항
- `REACT_PROTOCOL`: Thought → Action → Observation 형식
- `TOOL_POLICY`: 도구 사용 규칙
- `OUTPUT_CONTRACT`: 최종 markdown report 구조

Context Engineering 관점:

- Prompt는 “항상 들어가는 고정 컨텍스트”다.
- Prompt가 너무 길면 state와 retrieval context가 묻힌다.
- Prompt가 너무 짧으면 tool misuse, hallucination, output contract 위반이 늘어난다.
- Prompt는 versioning과 trace snapshot이 필요하다.

## 2.2 Message Context

LLM에게 전달되는 chat messages 배열이다.

예:

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT + "\n" + TOOL_POLICY},
    {"role": "user", "content": json.dumps({"state": state.snapshot()})},
]
```

Context Engineering 관점:

- LangGraph의 전체 state를 그대로 messages에 넣으면 context bloat가 생긴다.
- node별로 필요한 state만 projection해서 넣어야 한다.
- messages는 short-term memory로 쓰일 수 있지만, 무한 누적하면 distraction이 발생한다.

## 2.3 Graph State Context

LangGraph의 핵심 컨텍스트다. 공식 문서에서 LangGraph는 agent workflow를 graph로 모델링하며, 세 가지 핵심 요소를 사용한다고 설명한다.

- `State`: 현재 애플리케이션 snapshot을 나타내는 공유 데이터 구조
- `Nodes`: 현재 state를 받아 계산/side effect를 수행하고 state update를 반환하는 함수
- `Edges`: 현재 state에 따라 다음 node를 결정하는 함수

Context Engineering 관점에서 `State`는 “모델에게 모두 보여줄 텍스트”가 아니라 **컨텍스트 후보들의 구조화된 저장소**다.

좋은 state는 다음을 분리한다.

```text
사용자 요청          → request
원본 데이터          → rawLogs / documents / files
구조화된 중간 결과   → parsedRecords / metrics / anomalies
검색 컨텍스트        → ragContext
도구/외부 메타데이터 → mcpContext
증거                → evidence
추론 경로            → reactSteps
검증 결과            → validation
최종 산출물          → finalReport
오류                → errors
```

`reference_agent/weblog_agent/state.py`의 `WebLogAnalysisState`가 좋은 예다.

```python
@dataclass
class WebLogAnalysisState:
    request: Dict[str, Any]
    logSource: Dict[str, Any]
    rawLogs: Optional[Dict[str, Any]]
    parsedRecords: List[Dict[str, Any]]
    filteredRecords: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    baseline: Dict[str, Any]
    anomalies: List[Dict[str, Any]]
    evidence: Dict[str, Any]
    ragContext: List[Dict[str, Any]]
    mcpContext: Dict[str, Any]
    reactSteps: List[Dict[str, Any]]
    validation: Dict[str, Any]
    finalReport: Optional[str]
    errors: List[str]
```

## 2.4 Tool Observation Context

LangChain/LangGraph 에이전트는 도구 호출 결과를 통해 외부 세계를 관찰한다.

예:

- log file read result
- parsed records
- computed metrics
- RAG retrieved documents
- MCP service context
- API response
- database query result

Context Engineering 관점:

- tool output은 가장 빠르게 context를 비대하게 만든다.
- raw output과 model-facing summary를 분리해야 한다.
- 원본은 state/store/artifact로 보관하고, LLM에는 요약·통계·참조 ID만 전달하는 것이 좋다.

`reference_agent`에서도 `_summarize_observation()`이 `lines`, `records` 같은 큰 필드를 제거한다.

```python
def _summarize_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in observation.items() if k not in {"lines", "records"}}
```

이것은 Context Engineering의 **Compress** 전략이다.

## 2.5 Retrieval Context

LangChain/LangGraph에서 RAG retriever가 가져온 문서다.

예:

```python
state.ragContext = out.get("documents", [])
```

Context Engineering 관점:

- RAG context는 “측정된 evidence”가 아니라 “해석을 돕는 지식”으로 구분해야 한다.
- runbook은 원인 후보와 권장 조치에는 사용할 수 있지만, 실제 error rate 같은 수치 증거를 대체하면 안 된다.
- 각 chunk에는 `doc_id`, `score`, `source`, `content`가 있어야 한다.

`reference_agent/weblog_agent/rag.py`의 `RetrievedDocument` 구조가 이에 해당한다.

```python
@dataclass
class RetrievedDocument:
    doc_id: str
    score: float
    content: str
    source: str
```

## 2.6 Memory Context

LangGraph 공식 문서는 memory를 크게 두 가지로 설명한다.

1. **Short-term memory**: thread-scoped memory. 한 대화/스레드 안의 메시지와 state를 checkpointer로 유지.
2. **Long-term memory**: thread를 넘어 사용자 또는 애플리케이션 단위로 유지되는 memory. custom namespace에 저장.

Context Engineering 관점:

- short-term memory는 현재 thread의 state/checkpoint다.
- long-term memory는 별도 store에 저장하고 필요할 때만 select해야 한다.
- memory는 무조건 context에 넣는 것이 아니라, relevance/recency/permission 기준으로 선택한다.

## 2.7 Checkpoint Context

LangGraph의 persistence layer는 graph state를 checkpoint로 저장한다. 공식 문서에 따르면 checkpointer를 사용해 graph를 compile하면 실행 각 단계에서 state snapshot이 thread별로 저장되며, human-in-the-loop, conversational memory, time travel debugging, fault-tolerant execution을 가능하게 한다.

Context Engineering 관점:

- checkpoint는 “되돌릴 수 있는 context history”다.
- 실패한 node 이전 상태로 resume할 수 있다.
- 어떤 context가 어떤 결과를 만들었는지 time travel debugging이 가능하다.
- 잘못된 state update가 context poisoning을 만든 경우, 어느 checkpoint에서 오염됐는지 추적할 수 있다.

## 2.8 Trace / Observability Context

LangChain/LangGraph 운영에서는 LangSmith 또는 자체 trace를 통해 다음을 기록해야 한다.

- node start/end state snapshot
- edge selection reason
- LLM messages
- tool call input/output
- retrieval query/result
- validation result
- final output

`reference_agent/weblog_agent/trace.py`와 `graph.py`의 trace 이벤트가 이에 해당한다.

Context Engineering 관점:

- trace는 모델 입력이 아니라 운영자/평가자가 보는 meta-context다.
- agent drift, context bloat, tool misuse를 탐지하려면 trace가 필수다.

---

## 3. LangGraph의 State를 Context Engineering 단위로 설계하기

## 3.1 State는 “모든 것을 담는 가방”이 아니다

나쁜 state 설계:

```python
class State(TypedDict):
    messages: list
    everything: dict
```

문제:

- 어떤 node가 어떤 정보를 읽고 쓰는지 불명확하다.
- LLM call마다 전체 state를 넣게 된다.
- context bloat와 context confusion이 발생한다.
- 평가/검증이 어렵다.

좋은 state 설계:

```python
class AgentState(TypedDict):
    request: RequestContext
    task_state: TaskState
    evidence: EvidenceState
    retrieved_context: list[RetrievedChunk]
    tool_observations: list[ToolObservationSummary]
    validation: ValidationState
    errors: list[ErrorSummary]
    final: FinalOutput | None
```

핵심 원칙:

1. 원본 데이터와 LLM-facing 요약을 분리한다.
2. 측정된 evidence와 추론된 hypothesis를 분리한다.
3. RAG knowledge와 tool observation을 분리한다.
4. 사람이 검증할 validation state를 별도로 둔다.
5. final output은 마지막에만 생성한다.

## 3.2 Input / Internal / Output schema를 분리한다

LangGraph는 input/output schema와 internal state schema를 분리할 수 있다. Context Engineering 관점에서 이는 매우 중요하다.

예:

```python
from typing_extensions import TypedDict

class InputState(TypedDict):
    user_input: str
    access_log_path: str

class OutputState(TypedDict):
    final_report: str
    validation_passed: bool

class InternalState(TypedDict):
    user_input: str
    access_log_path: str
    request: dict
    raw_log_ref: str | None
    parsed_record_count: int
    metrics: dict
    anomalies: list[dict]
    rag_context: list[dict]
    mcp_context: dict
    evidence: dict
    validation: dict
    final_report: str | None
```

장점:

- 외부 사용자는 필요한 입력/출력만 본다.
- 내부 context channel은 graph 내부에서만 관리된다.
- 민감하거나 큰 데이터가 final output으로 새지 않는다.

## 3.3 Private state channel 사용

LangGraph 문서는 private state channel을 통해 내부 node 간 통신을 할 수 있다고 설명한다. Context Engineering에서는 다음 용도로 유용하다.

- LLM에게 보여주지 않을 내부 점수
- retrieval 후보 전체
- validation intermediate result
- raw tool output reference
- redaction map
- prompt assembly debug info

예:

```python
class PrivateContext(TypedDict):
    retrieval_candidates: list[dict]
    redaction_map: dict[str, str]
    raw_tool_output_uri: str
    context_budget_report: dict
```

## 3.4 Reducer 설계

LangGraph state key는 reducer를 통해 node update가 적용된다. Context Engineering 관점에서 reducer는 “컨텍스트가 누적되는 방식”을 결정한다.

나쁜 예:

```python
messages: list  # 계속 append만 함
```

문제:

- 긴 대화가 무한히 누적된다.
- 오래된 tool observation이 계속 영향을 준다.

좋은 예:

```python
from typing import Annotated
from operator import add

class State(TypedDict):
    observations: Annotated[list[ObservationSummary], add]
    errors: Annotated[list[ErrorSummary], add]
    current_context_pack: ContextPack
```

그리고 별도 node에서 compression을 수행한다.

```python
def compress_observations(state: State) -> dict:
    if len(state["observations"]) < 20:
        return {}
    summary = summarize_observations(state["observations"])
    return {
        "observations": [summary],
        "context_compression_count": state.get("context_compression_count", 0) + 1,
    }
```

실제로 reducer가 append-only인지 overwrite인지에 따라 context poisoning과 bloat의 양상이 달라진다.

---

## 4. Node를 Context Boundary로 설계하기

LangGraph에서 node는 단순 함수다. 그러나 Context Engineering 관점에서는 node가 **컨텍스트 경계(context boundary)**다.

각 node는 다음을 명확히 해야 한다.

```yaml
node:
  name: retrieve_runbook
  reads:
    - request.targetPath
    - request.rawUserInput
  writes:
    - ragContext
  llm_context:
    - none 또는 query generation용 최소 context
  tools:
    - retriever
  output_summary:
    - doc_id
    - score
    - source
    - excerpt
  raw_output_policy:
    - store externally if large
```

## 4.1 Node별 context projection

LLM node가 전체 state를 보는 것은 위험하다. node마다 필요한 정보만 projection한다.

예:

```python
def build_react_decision_context(state: WebLogAnalysisState) -> dict:
    return {
        "request": state.request,
        "progress": {
            "has_raw_logs": state.rawLogs is not None,
            "parsedRecordCount": len(state.parsedRecords),
            "filteredRecordCount": len(state.filteredRecords),
            "has_metrics": bool(state.metrics),
            "has_anomalies": bool(state.anomalies),
            "has_rag": bool(state.ragContext),
            "has_mcp": bool(state.mcpContext),
            "has_evidence": bool(state.evidence.get("logLines")),
        },
        "errors": state.errors[-3:],
        "availableTools": select_tools_for_current_state(state),
    }
```

이 방식은 `state.snapshot()` 전체를 넣는 것보다 안전하다.

## 4.2 Deterministic node와 LLM node 분리

좋은 LangGraph 에이전트는 모든 것을 LLM에게 맡기지 않는다.

Deterministic node 예:

- parse request
- read file
- parse access log
- filter records
- compute metrics
- validate schema
- redact PII

LLM node 예:

- ambiguous intent clarification
- next action selection
- hypothesis generation
- final narrative report

Context Engineering 관점:

- 숫자/판정/필터링은 deterministic code로 계산한다.
- LLM은 판단과 설명에 집중시킨다.
- deterministic output은 LLM에게 evidence로 제공한다.

`reference_agent`도 `compute_log_metrics`는 deterministic tool로 계산하고, LLM에게 수치를 만들게 하지 않는다.

## 4.3 Node contract 문서화

각 node는 다음 contract를 가져야 한다.

```markdown
## Node: compute_log_metrics

Purpose:
- filteredRecords에서 request_count, error_rate, latency percentile 계산

Reads:
- filteredRecords

Writes:
- metrics

LLM visible output:
- request_count
- error_count
- error_rate
- p95_latency_ms
- p99_latency_ms

Hidden/raw output:
- 없음

Failure policy:
- filteredRecords가 비어 있으면 metric=0과 warning 반환

Context risks:
- LLM이 metric을 추측하면 안 됨
- parse_error_count가 높으면 confidence 낮춤
```

---

## 5. Edge를 Context Flow Control로 설계하기

LangGraph의 edge는 다음 node를 선택한다. Context Engineering 관점에서 edge는 **어떤 컨텍스트를 더 수집해야 하는지**를 결정하는 control flow다.

## 5.1 Fixed edge

예:

```text
initialize_agent → react_agent → validate_findings → finalize
```

적합한 경우:

- 순서가 명확한 workflow
- 검증/정리 단계가 항상 필요한 경우

## 5.2 Conditional edge

예:

```python
def route_after_metrics(state: State) -> str:
    if not state["metrics"]:
        return "compute_metrics"
    if state["metrics"].get("error_rate", 0) > 0.05:
        return "retrieve_runbook"
    return "finalize"
```

Context Engineering 장점:

- 불필요한 RAG/tool context를 줄일 수 있다.
- 필요한 경우에만 비싼 도구를 호출한다.
- 정보가 부족한 상태에서 final answer로 가는 것을 막는다.

## 5.3 ReAct loop edge

ReAct agent에서는 LLM이 다음 action을 고른다.

```text
Thought → Action → Observation → Thought → ... → Finish
```

Context Engineering 포인트:

- available tools를 매 step 동적으로 제한한다.
- max_steps를 둔다.
- finish 조건을 명확히 한다.
- observation summary만 다음 step에 넣는다.
- 이미 수집된 evidence가 있으면 중복 tool call을 막는다.

`reference_agent`는 `_fallback_action()`으로 deterministic next action policy를 제공한다. 이는 LLM decision 실패 시 context flow를 안정화하는 좋은 패턴이다.

---

## 6. LangChain Tool / LangGraph Tool Node의 Context Engineering

## 6.1 Tool description도 컨텍스트다

LangChain tool의 이름, 설명, schema는 모두 LLM context에 들어갈 수 있다. 따라서 tool description은 짧고 정확해야 한다.

나쁜 예:

```text
analyze: This tool can analyze many kinds of things and maybe find problems.
```

좋은 예:

```text
compute_log_metrics: Compute request count, error count, error rate, and latency percentiles from already-filtered web access log records. Use for quantitative metric claims.
```

## 6.2 Tool exposure는 동적이어야 한다

모든 tool을 항상 보여주면 context confusion이 발생한다.

예:

```python
def select_tools_for_current_state(state):
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
    if not state.evidence.get("logLines"):
        return ["collect_evidence"]
    return ["finish"]
```

이 방식은 ReAct agent의 drift를 줄인다.

## 6.3 Tool output은 raw와 summary로 분리한다

예:

```python
raw_result = read_log_file(path)
state.raw_log_ref = save_artifact(raw_result["lines"])
state.rawLogs = {
    "lineCount": raw_result["line_count"],
    "truncated": raw_result["truncated"],
    "artifactRef": state.raw_log_ref,
}
```

LLM에게는 다음만 보여준다.

```json
{
  "lineCount": 10000,
  "truncated": false,
  "artifactRef": "artifact://logs/run-123/raw-log"
}
```

## 6.4 Side-effect tool은 승인 gate를 둔다

LangGraph에서는 interrupt/human-in-the-loop과 checkpoint를 사용해 승인 workflow를 구성할 수 있다.

예:

```text
draft_action
  → if side_effect_required:
        interrupt_for_approval
        → approved: execute_tool
        → rejected: revise_plan
  → finalize
```

Context Engineering 관점:

- 승인 전에는 destructive/external tool을 LLM에게 노출하지 않는다.
- 승인 요청에는 tool input, reason, expected effect, rollback plan을 포함한다.
- 승인 후 checkpoint에서 resume한다.

---

## 7. LangGraph Memory 설계

## 7.1 Short-term memory: thread state와 checkpoint

LangGraph에서 short-term memory는 thread-scoped state다.

사용 예:

```python
config = {"configurable": {"thread_id": "incident-2026-05-15-api-login"}}
graph.invoke(input_state, config=config)
```

Context Engineering 포인트:

- thread_id는 사용자/세션/사건 단위로 명확히 만든다.
- 같은 thread에서는 이전 checkpoint state를 이어받는다.
- thread가 너무 오래 지속되면 summary/compaction node를 둔다.

## 7.2 Long-term memory: Store와 namespace

Long-term memory는 thread 밖에 저장되는 기억이다.

예시 namespace:

```text
("user", user_id, "preferences")
("service", service_name, "runbook_insights")
("agent", agent_name, "procedures")
("incident", service_name, "postmortem_summaries")
```

Context Engineering 포인트:

- long-term memory를 무조건 주입하지 않는다.
- namespace, relevance score, recency, sensitivity로 필터링한다.
- memory에는 source와 confidence를 저장한다.

## 7.3 Memory write policy

LangGraph 에이전트에서 memory write는 두 방식이 있다.

1. Hot path write
   - 사용자 응답 전에 memory update
   - 최신성이 좋지만 latency와 오류 위험 증가

2. Background write
   - run 종료 후 별도 job으로 memory 생성
   - 사용자 응답은 빠르지만 memory 반영이 늦음

정책 예:

```yaml
memory_write_policy:
  hot_path:
    allow:
      - explicit user correction
      - current incident critical fact
    deny:
      - inferred preference
      - noisy intermediate thought
  background:
    allow:
      - stable user preference
      - repeated workflow pattern
      - resolved incident summary
```

## 7.4 Memory retrieval policy

```yaml
memory_retrieval_policy:
  max_items: 5
  min_relevance: 0.75
  prefer:
    - explicit user statements
    - recent validated facts
    - procedural rules for current task
  exclude:
    - sensitive data unless required
    - stale incident hypotheses
    - memories without source
```

---

## 8. RAG를 LangGraph Node로 설계하기

## 8.1 RAG는 하나의 node가 아니라 pipeline이다

단순한 `retriever.invoke(query)`만으로 끝내면 안 된다. LangGraph에서는 RAG pipeline을 여러 node로 나눌 수 있다.

```text
query_understanding
  → retrieve_candidates
  → rerank_context
  → compress_context
  → validate_context
  → answer_or_next_tool
```

각 단계는 state를 읽고 쓴다.

```python
class RagState(TypedDict):
    user_query: str
    rewritten_query: str
    retrieval_candidates: list[dict]
    selected_chunks: list[dict]
    context_conflicts: list[dict]
    context_pack: str
```

## 8.2 Query rewriting node

```python
def rewrite_query(state: State) -> dict:
    return {
        "rewritten_query": f"{state['request']['targetPath']} incident runbook error_rate latency deployment dependencies"
    }
```

## 8.3 Retrieval node

```python
def retrieve_runbook(state: State) -> dict:
    docs = retriever.invoke(state["rewritten_query"])
    return {"retrieval_candidates": docs}
```

## 8.4 Rerank/select node

```python
def select_context(state: State) -> dict:
    selected = []
    for doc in state["retrieval_candidates"]:
        if doc["score"] >= 0.6 and has_permission(doc):
            selected.append({
                "doc_id": doc["doc_id"],
                "source": doc["source"],
                "score": doc["score"],
                "excerpt": trim(doc["content"], max_tokens=500),
            })
    return {"selected_chunks": selected[:5]}
```

## 8.5 RAG context의 신분 구분

RAG 문서는 다음 중 어느 역할인지 명확히 해야 한다.

| RAG 유형 | 역할 | 답변에서의 취급 |
|---|---|---|
| 정책 문서 | authoritative source | 근거로 인용 가능 |
| runbook | operational guidance | 원인 후보/조치 제안에 사용 |
| 과거 incident | episodic reference | 유사 사례로만 사용 |
| 블로그/외부 문서 | background knowledge | 보조 설명에만 사용 |

`reference_agent`의 runbook은 “측정 evidence”가 아니라 “RAG Context”로 따로 표시되어야 한다.

---

## 9. ReAct 에이전트의 Context Engineering

## 9.1 ReAct에서 컨텍스트가 망가지는 방식

ReAct는 강력하지만 다음 문제가 자주 발생한다.

1. Thought가 길어져 context bloat 발생
2. Observation에 raw data가 누적됨
3. 이미 한 tool call을 반복함
4. 충분한 evidence 없이 finish함
5. RAG 문서를 measured evidence처럼 사용함
6. tool error를 무시하고 계속 진행함
7. tool list가 많아 잘못된 action 선택

## 9.2 ReAct step context 최소화

매 step마다 LLM에게 줄 context는 다음 정도면 충분한 경우가 많다.

```json
{
  "step": 4,
  "goal": "Analyze /api/login 5xx spike from web logs",
  "progress": {
    "request_parsed": true,
    "logs_loaded": true,
    "records_parsed": true,
    "records_filtered": false,
    "metrics_computed": false,
    "runbook_retrieved": false,
    "service_context_loaded": false,
    "evidence_collected": false
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

## 9.3 Thought 저장 정책

Thought를 모두 저장할 필요는 없다. 운영과 평가에는 다음이 더 유용하다.

```json
{
  "step": 4,
  "decision_reason": "Need records scoped to target endpoint before computing metrics",
  "action": "filter_log_records",
  "input_summary": {"path_pattern": "/api/login", "status_min": 0, "status_max": 599}
}
```

즉, 내부 추론 전체보다 **decision rationale summary**를 저장한다.

## 9.4 Finish gate

ReAct agent가 final answer를 내기 전에 다음 gate를 통과하게 한다.

```python
def can_finish(state: WebLogAnalysisState) -> tuple[bool, list[str]]:
    missing = []
    if not state.request.get("targetPath"):
        missing.append("targetPath")
    if not state.metrics:
        missing.append("metrics")
    if not state.anomalies:
        missing.append("anomaly_check")
    if not state.evidence.get("logLines"):
        missing.append("evidence")
    if not state.ragContext:
        missing.append("rag_context")
    if not state.mcpContext:
        missing.append("mcp_context")
    return (not missing, missing)
```

이 gate는 prompt보다 강력하다. Prompt에 “충분한 증거 없이 끝내지 마”라고 쓰는 것보다, edge/node에서 finish를 막는 것이 안전하다.

---

## 10. Context Compression 패턴

## 10.1 Tool observation compression

원본:

```json
{
  "records": [10000개의 로그 record],
  "parse_error_count": 2,
  "total_lines": 10000
}
```

LLM-facing summary:

```json
{
  "record_count": 9998,
  "parse_error_count": 2,
  "parse_error_rate": 0.0002,
  "raw_record_ref": "artifact://run-123/parsed-records"
}
```

## 10.2 State snapshot compression

`state.snapshot()`은 다음 기준을 따른다.

- list 원문 대신 count
- raw data 대신 artifact reference
- evidence는 대표 샘플만
- errors는 최근 N개
- ragContext는 doc_id/source/excerpt만

`reference_agent`의 `snapshot()`은 `rawLogs`에서 line count와 truncated만 남긴다. 좋은 방향이다.

추가 개선 예:

```python
def snapshot_for_llm(state):
    return {
        "request": state.request,
        "counts": {
            "parsed": len(state.parsedRecords),
            "filtered": len(state.filteredRecords),
            "rag": len(state.ragContext),
            "react_steps": len(state.reactSteps),
        },
        "metrics": state.metrics,
        "anomalies": state.anomalies,
        "evidence_summary": {
            "logLineCount": len(state.evidence.get("logLines", [])),
            "metricRefs": state.evidence.get("metricRefs", []),
        },
        "errors": state.errors[-3:],
    }
```

## 10.3 Conversation/message trimming

LangGraph memory guide는 긴 대화에서 message list를 수동으로 제거하거나 잊는 기법이 필요하다고 설명한다.

실무 패턴:

```text
messages
  → keep system/developer instruction
  → keep latest user request
  → keep unresolved decisions
  → summarize older conversation
  → drop stale tool observations
```

## 10.4 Error compaction

LangGraph node 실패 시 checkpoint로 resume할 수 있지만, 오류 전체를 LLM context에 넣을 필요는 없다.

```json
{
  "error_type": "FileNotFoundError",
  "node": "read_log_file",
  "message": "log file not found",
  "input_summary": {"path": "/var/log/nginx/access.log"},
  "retryable": true,
  "next_action": "ask user for valid path or check fixture path"
}
```

---

## 11. Context Isolation 패턴

## 11.1 Subgraph로 격리하기

LangGraph에서는 복잡한 workflow를 subgraph로 나눌 수 있다. Context Engineering 관점에서 subgraph는 격리된 context domain이다.

예:

```text
main_graph
  ├─ request_parsing_subgraph
  ├─ log_analysis_subgraph
  ├─ rag_context_subgraph
  ├─ validation_subgraph
  └─ reporting_subgraph
```

장점:

- 각 subgraph의 state schema를 좁힐 수 있다.
- checkpoint namespace로 subgraph 상태를 구분할 수 있다.
- node별 context risk를 줄인다.

## 11.2 Agent role별 격리

Multi-agent 구조에서는 role별 context를 분리한다.

```text
Incident Analyzer
  - metrics/evidence 중심

Runbook Researcher
  - RAG/runbook 중심

Service Metadata Agent
  - MCP/service context 중심

Report Writer
  - validated summary만 사용

Judge/Validator
  - final report와 evidence alignment 검증
```

## 11.3 Tool 권한 격리

각 node/subgraph가 사용할 수 있는 tool을 제한한다.

```yaml
log_analysis_subgraph:
  tools:
    - read_log_file
    - parse_access_log
    - filter_log_records
    - compute_log_metrics

rag_subgraph:
  tools:
    - retrieve_runbook

metadata_subgraph:
  tools:
    - get_service_context

reporting_subgraph:
  tools: []
```

이렇게 하면 report writer가 갑자기 파일을 읽거나 외부 API를 호출하는 것을 막을 수 있다.

---

## 12. Persistence와 Human-in-the-loop

## 12.1 Checkpointer 사용

LangGraph persistence 문서는 checkpointer가 graph state를 각 step에서 thread별 checkpoint로 저장한다고 설명한다.

예:

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "incident-001"}}

graph.invoke(input_state, config=config)
```

운영에서는 InMemory가 아니라 SQLite/Postgres/managed checkpointer 등을 사용한다.

## 12.2 Context Engineering 이점

- 어떤 node에서 잘못된 context가 들어갔는지 찾을 수 있다.
- human approval 전 state를 보존할 수 있다.
- 실패 후 성공한 node를 재실행하지 않고 resume할 수 있다.
- time travel로 다른 retrieval/tool 선택을 실험할 수 있다.

## 12.3 Human approval context pack

사람에게 승인 요청할 때는 LLM 대화 전체가 아니라 승인에 필요한 context만 보여준다.

```json
{
  "approval_type": "execute_external_action",
  "proposed_action": "restart_service",
  "reason": "error_rate critical and runbook recommends restart after dependency health check",
  "evidence": {
    "error_rate": 0.124,
    "request_count": 1000,
    "log_samples": ["..."]
  },
  "risk": "temporary downtime for active users",
  "rollback": "cancel restart before execution or redeploy previous version",
  "source_refs": ["runbook-2", "mcp-service-context"]
}
```

---

## 13. Validation과 Judge Agent 관점

LangChain/LangGraph 에이전트의 Context Engineering은 평가 가능한 형태여야 한다. 특히 이 저장소의 `judge-agent` 목적과 연결하면, agent trace에서 다음 drift를 감지할 수 있다.

## 13.1 평가해야 할 drift 유형

| Drift 유형 | 설명 | Trace 신호 |
|---|---|---|
| Goal drift | 원래 목표에서 벗어남 | request와 final output 불일치 |
| Tool drift | 잘못된 도구 선택 | available tool/state 대비 action 부적절 |
| Memory drift | 관련 없는 기억 사용 | memory retrieval relevance 낮음 |
| RAG drift | 검색 문서를 잘못 사용 | RAG context와 claim 불일치 |
| Evidence drift | evidence 없이 수치/원인 주장 | metric tool call 없이 metric claim |
| Handoff drift | subagent/다음 node 전달 과정에서 의미 변형 | node output과 next node input 불일치 |
| Context bloat | 불필요한 context 과다 | token count 증가, raw records/messages 주입 |
| Context poisoning | 잘못된 중간 가정이 이후 state에 고착 | early error/hypothesis가 final claim으로 승격 |

## 13.2 Trace event schema

LangGraph 에이전트는 최소한 다음 이벤트를 남기는 것이 좋다.

```json
{
  "event_type": "node_start",
  "run_id": "",
  "thread_id": "",
  "node": "",
  "state_snapshot": {},
  "context_budget": {
    "input_tokens_estimate": 0,
    "state_tokens": 0,
    "retrieval_tokens": 0,
    "tool_tokens": 0
  }
}
```

```json
{
  "event_type": "llm_start",
  "node": "react_agent",
  "messages": [],
  "tools_exposed": [],
  "state_projection_keys": [],
  "retrieved_context_ids": [],
  "memory_ids": []
}
```

```json
{
  "event_type": "tool_end",
  "tool": "compute_log_metrics",
  "input_summary": {},
  "output_summary": {},
  "raw_output_ref": "artifact://..."
}
```

```json
{
  "event_type": "validation_result",
  "checks": [
    "metrics_present",
    "anomalies_have_evidence",
    "rag_context_present",
    "mcp_context_present",
    "output_contract"
  ],
  "passed": true,
  "issues": []
}
```

## 13.3 Context Engineering 평가 항목

```yaml
context_engineering_eval:
  state_design:
    - raw data separated from summaries
    - evidence separated from hypotheses
    - validation state present
  prompt_design:
    - tool policy present
    - output contract present
    - hallucination constraints present
  tool_use:
    - quantitative claims backed by tools
    - no repeated unnecessary tool calls
    - side effects gated
  rag:
    - retrieved context relevant
    - sources preserved
    - RAG not treated as measurement
  compression:
    - raw tool outputs not injected into LLM
    - observations summarized
    - errors compacted
  isolation:
    - node/subgraph boundaries clear
    - tool access scoped
  persistence:
    - thread_id used
    - checkpoints available
  observability:
    - node/edge/llm/tool/retrieval traces available
```

---

## 14. `reference_agent/weblog_agent`에 대한 Context Engineering 해석

## 14.1 현재 구조

`reference_agent/weblog_agent`는 LangGraph/LangChain-style ReAct reference agent다. 실제 LangGraph dependency를 무겁게 쓰지는 않지만, graph, prompts, ReAct loop, trace event가 LangGraph ReAct agent의 형태를 모사한다.

구성:

```text
reference_agent/weblog_agent/
  graph.py       # ReAct loop, node/edge orchestration
  state.py       # WebLogAnalysisState
  prompts.py     # system prompt, ReAct protocol, tool policy, output contract
  tools.py       # deterministic log tools
  rag.py         # LocalRunbookRetriever
  mcp.py         # MCP service context client
  trace.py       # trace logging
  validation.py  # final validation
```

## 14.2 좋은 점

1. State가 도메인별로 구조화되어 있다.
2. 원본 로그와 snapshot을 분리한다.
3. 수치 계산을 LLM이 아니라 deterministic tool이 수행한다.
4. RAG context와 MCP context를 별도 필드로 둔다.
5. validation node가 있다.
6. trace가 node/edge/tool/llm 단위로 남는다.
7. output contract가 명시되어 있다.
8. max_steps로 ReAct loop runaway를 제한한다.
9. fallback action policy가 있어 LLM 실패 시에도 진행 가능하다.

## 14.3 개선할 수 있는 점

### 14.3.1 LLM에 전달되는 state projection 더 축소

현재 `_next_react_action()`은 `state.snapshot()`을 JSON으로 넣는다. snapshot이 커지면 context bloat가 생길 수 있다.

개선:

```python
def react_decision_projection(state):
    return {
        "goal": state.request.get("rawUserInput"),
        "targetPath": state.request.get("targetPath"),
        "progress": progress_flags(state),
        "lastStep": state.reactSteps[-1] if state.reactSteps else None,
        "metricsPresent": bool(state.metrics),
        "anomalyCount": len(state.anomalies),
        "evidencePresent": bool(state.evidence.get("logLines")),
        "errors": state.errors[-2:],
    }
```

### 14.3.2 availableTools 동적 축소

현재 LLM에는 `self.tool_names()` 전체가 전달된다. step에 따라 필요한 도구만 보여주는 방식이 더 안전하다.

```python
{"availableTools": self.select_available_tools(state)}
```

### 14.3.3 RAG context role 강화

Prompt에 이미 “RAG runbook content only as contextual guidance”가 있지만, final report 생성 시에도 RAG context를 별도 category로 제공하는 것이 좋다.

```json
{
  "measuredEvidence": {...},
  "retrievedGuidance": {...},
  "serviceMetadata": {...},
  "hypotheses": [...]
}
```

### 14.3.4 Context budget trace 추가

각 LLM call마다 다음을 trace한다.

```json
{
  "context_budget": {
    "system_chars": 1200,
    "state_chars": 2400,
    "tool_description_chars": 900,
    "retrieval_chars": 1800,
    "total_chars": 6300
  }
}
```

### 14.3.5 Finish gate를 코드로 강제

LLM이 `finish`를 반환해도 `can_finish()`가 false면 다음 tool로 route한다.

```python
if name == "finish":
    ok, missing = can_finish(state)
    if not ok:
        state.errors.append(f"Finish blocked; missing: {missing}")
        return self._fallback_action(state)
```

---

## 15. 권장 LangGraph 구현 패턴

## 15.1 Production-grade graph skeleton

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class IncidentInput(TypedDict):
    user_input: str
    access_log_path: str

class IncidentOutput(TypedDict):
    final_report: str
    validation: dict

class IncidentState(TypedDict):
    user_input: str
    access_log_path: str
    request: dict
    raw_log_ref: str | None
    parsed_summary: dict
    metrics: dict
    anomalies: list[dict]
    rag_context: list[dict]
    mcp_context: dict
    evidence: dict
    errors: list[dict]
    validation: dict
    final_report: str | None

builder = StateGraph(
    IncidentState,
    input_schema=IncidentInput,
    output_schema=IncidentOutput,
)

builder.add_node("parse_request", parse_request)
builder.add_node("load_logs", load_logs)
builder.add_node("parse_logs", parse_logs)
builder.add_node("filter_records", filter_records)
builder.add_node("compute_metrics", compute_metrics)
builder.add_node("detect_anomalies", detect_anomalies)
builder.add_node("retrieve_runbook", retrieve_runbook)
builder.add_node("get_service_context", get_service_context)
builder.add_node("collect_evidence", collect_evidence)
builder.add_node("validate", validate)
builder.add_node("write_report", write_report)

builder.add_edge(START, "parse_request")
builder.add_edge("parse_request", "load_logs")
builder.add_edge("load_logs", "parse_logs")
builder.add_edge("parse_logs", "filter_records")
builder.add_edge("filter_records", "compute_metrics")
builder.add_edge("compute_metrics", "detect_anomalies")
builder.add_edge("detect_anomalies", "retrieve_runbook")
builder.add_edge("retrieve_runbook", "get_service_context")
builder.add_edge("get_service_context", "collect_evidence")
builder.add_edge("collect_evidence", "validate")
builder.add_edge("validate", "write_report")
builder.add_edge("write_report", END)

graph = builder.compile(checkpointer=checkpointer)
```

## 15.2 ReAct + deterministic rails hybrid

완전 자유 ReAct보다 다음 구조가 안전하다.

```text
Deterministic preprocessing
  → constrained ReAct loop
  → deterministic validation
  → LLM report writing
  → final validation
```

예:

```text
parse_request → load/parse/filter/metrics
  → ReAct only for deciding additional context needs
  → validate evidence
  → write report
```

## 15.3 Context Builder 함수 분리

LLM call 내부에서 즉석으로 prompt를 만들지 말고, context builder를 분리한다.

```python
def build_final_report_context(state: IncidentState) -> dict:
    return {
        "request": state["request"],
        "metrics": state["metrics"],
        "anomalies": state["anomalies"],
        "evidence": state["evidence"],
        "ragContext": [compact_doc(d) for d in state["rag_context"]],
        "mcpContext": state["mcp_context"],
        "limitations": collect_limitations(state),
    }
```

장점:

- 테스트 가능
- token budget 측정 가능
- redaction 적용 가능
- judge agent가 context quality를 평가하기 쉬움

---

## 16. LangChain/LangGraph Context Engineering 체크리스트

## 16.1 State

- [ ] input/internal/output schema가 분리되어 있는가?
- [ ] raw data와 summary가 분리되어 있는가?
- [ ] evidence와 hypothesis가 분리되어 있는가?
- [ ] RAG, MCP, tool observation이 별도 필드인가?
- [ ] validation state가 있는가?
- [ ] errors가 구조화되어 있는가?
- [ ] snapshot이 LLM-facing으로 압축되어 있는가?

## 16.2 Node

- [ ] 각 node의 read/write state가 명확한가?
- [ ] LLM node와 deterministic node가 분리되어 있는가?
- [ ] node별 context projection이 있는가?
- [ ] 큰 output은 artifact/store에 저장하고 summary만 state에 남기는가?
- [ ] node failure policy가 있는가?

## 16.3 Edge

- [ ] next step 조건이 명확한가?
- [ ] 충분한 evidence 없이 finalize로 가지 않는가?
- [ ] 반복 loop에 max_steps가 있는가?
- [ ] conditional edge가 불필요한 retrieval/tool call을 줄이는가?

## 16.4 Tool

- [ ] tool description이 짧고 명확한가?
- [ ] tool schema가 엄격한가?
- [ ] tool exposure가 동적인가?
- [ ] side-effect tool에 approval gate가 있는가?
- [ ] tool output이 summary/raw로 분리되는가?

## 16.5 RAG

- [ ] query rewriting이 있는가?
- [ ] metadata/source/doc_id가 유지되는가?
- [ ] reranking 또는 filtering이 있는가?
- [ ] retrieved context의 역할(authoritative/guidance/reference)이 구분되는가?
- [ ] RAG와 measured evidence가 분리되는가?

## 16.6 Memory/Persistence

- [ ] thread_id를 명확히 사용하는가?
- [ ] checkpointer가 설정되어 있는가?
- [ ] short-term memory compaction이 있는가?
- [ ] long-term memory namespace가 정의되어 있는가?
- [ ] memory retrieval/write policy가 있는가?

## 16.7 Observability

- [ ] node_start/node_end trace가 있는가?
- [ ] edge_selected reason이 기록되는가?
- [ ] LLM messages 또는 안전한 projection이 기록되는가?
- [ ] tool input/output summary가 기록되는가?
- [ ] retrieval query/result가 기록되는가?
- [ ] context budget이 측정되는가?
- [ ] validation result가 기록되는가?

---

## 17. 실무 설계 예시: WebLog Analysis Agent

## 17.1 Context map

```yaml
agent: weblog-analysis-agent
framework: langgraph/langchain-style
architecture: constrained-react-workflow

context_sources:
  instruction:
    - SYSTEM_PROMPT
    - REACT_PROTOCOL
    - TOOL_POLICY
    - OUTPUT_CONTRACT
  user:
    - rawUserInput
    - targetPath
    - requestedMetrics
  raw_data:
    - access log file
  deterministic_evidence:
    - parsed records
    - filtered records
    - computed metrics
    - anomaly detection
  retrieved_knowledge:
    - runbook chunks
  external_metadata:
    - MCP service context
  operational_state:
    - reactSteps
    - validation
    - errors
```

## 17.2 Recommended graph

```text
START
  → initialize_context
  → parse_user_request
  → read_log_file
  → parse_access_log
  → filter_log_records
  → compute_log_metrics
  → detect_log_anomalies
  → retrieve_runbook
  → get_service_context
  → collect_evidence
  → validate_findings
  → generate_report
  → validate_report
  → END
```

ReAct가 필요한 경우:

```text
START
  → initialize_context
  → deterministic_minimum_evidence
  → react_decide_additional_context
      ↺ tool observation summary
  → validate_findings
  → generate_report
  → END
```

## 17.3 Output contract

```markdown
## Summary
- measured finding만 요약

## Key Metrics
- deterministic metric tool 결과만 사용

## Anomalies
- anomaly detection 결과와 threshold 명시

## Evidence
- 대표 log lines와 metric refs

## RAG Context
- runbook에서 가져온 참고 정보

## MCP Context
- owner/SLO/deployment/dependency metadata

## Likely Causes
- evidence 기반 원인과 hypothesis 구분

## Recommended Actions
- runbook + evidence 기반 조치

## Confidence & Limitations
- parse error, missing baseline, truncated logs 등
```

## 17.4 Claim validation rule

```yaml
claim_validation:
  quantitative_claim:
    requires:
      - compute_log_metrics tool result
  anomaly_claim:
    requires:
      - detect_log_anomalies result
      - metric reference
  owner_or_slo_claim:
    requires:
      - MCP service context
  likely_cause_claim:
    requires_any:
      - log evidence
      - runbook guidance marked as hypothesis
      - deployment metadata
  recommendation:
    requires:
      - runbook or deterministic operational rule
```

---

## 18. Anti-patterns

## 18.1 전체 state를 무조건 LLM에 넣기

문제:

- context bloat
- irrelevant context distraction
- 민감 정보 노출

대안:

- node별 context projection
- snapshot_for_llm
- context budget

## 18.2 messages를 memory로 무한 사용

문제:

- 긴 대화에서 성능 저하
- stale instruction 영향

대안:

- thread state summary
- message trimming
- long-term memory select

## 18.3 모든 tool을 항상 노출

문제:

- tool confusion
- 잘못된 side-effect

대안:

- state 기반 tool selection
- tool groups
- approval gate

## 18.4 RAG 문서를 사실 측정값처럼 사용

문제:

- runbook에 “일반적 원인”이 있다고 해서 현재 incident 원인이라고 단정

대안:

- measured evidence와 retrieved guidance 분리
- hypothesis label

## 18.5 Validation을 prompt에만 맡기기

문제:

- 모델이 스스로 규칙 위반을 못 볼 수 있음

대안:

- deterministic validation node
- judge model 또는 rule-based checker
- final gate

## 18.6 Checkpoint 없이 장기 실행

문제:

- 실패 시 재시작 불가
- human approval workflow 어려움
- context poisoning 지점 추적 어려움

대안:

- checkpointer 사용
- thread_id 설계
- time travel debugging

---

## 19. 구현 템플릿

## 19.1 Context projection template

```python
def project_context_for_node(state: State, node_name: str) -> dict:
    if node_name == "react_decide":
        return {
            "request": state["request"],
            "progress": progress_flags(state),
            "last_observation": state.get("last_observation"),
            "available_tools": select_tools(state),
            "errors": state.get("errors", [])[-3:],
        }
    if node_name == "write_report":
        return {
            "request": state["request"],
            "metrics": state["metrics"],
            "anomalies": state["anomalies"],
            "evidence": state["evidence"],
            "rag_context": compact_rag(state["rag_context"]),
            "mcp_context": state["mcp_context"],
            "limitations": limitations(state),
        }
    raise ValueError(node_name)
```

## 19.2 Context budget template

```python
def estimate_context_budget(context: dict) -> dict:
    sections = {
        "instruction": context.get("instruction", ""),
        "state": context.get("state", {}),
        "retrieval": context.get("retrieval", []),
        "tools": context.get("tools", []),
        "memory": context.get("memory", []),
    }
    return {
        key: len(json.dumps(value, ensure_ascii=False))
        for key, value in sections.items()
    } | {"total_chars": sum(len(json.dumps(v, ensure_ascii=False)) for v in sections.values())}
```

## 19.3 Validation node template

```python
def validate_context_and_claims(state: State) -> dict:
    issues = []

    if state["final_report"]:
        claims = extract_claims(state["final_report"])
        for claim in claims:
            if claim["type"] == "metric" and not state.get("metrics"):
                issues.append({"type": "unsupported_metric_claim", "claim": claim})
            if claim["type"] == "owner" and not state.get("mcp_context"):
                issues.append({"type": "unsupported_owner_claim", "claim": claim})
            if claim["type"] == "cause" and not has_evidence_or_hypothesis_label(claim, state):
                issues.append({"type": "unsupported_cause_claim", "claim": claim})

    return {"validation": {"passed": not issues, "issues": issues}}
```

## 19.4 Dynamic tool selection template

```python
def select_tools(state: State) -> list[str]:
    if not state.get("request", {}).get("targetPath"):
        return ["parse_user_request"]
    if not state.get("raw_log_ref"):
        return ["read_log_file"]
    if not state.get("parsed_summary"):
        return ["parse_access_log"]
    if not state.get("metrics"):
        return ["compute_log_metrics"]
    if not state.get("rag_context"):
        return ["retrieve_runbook"]
    if not state.get("mcp_context"):
        return ["get_service_context"]
    return ["finish"]
```

---

## 20. 출처와 참고자료

1. LangGraph Graph API overview  
   https://docs.langchain.com/oss/python/langgraph/graph-api

2. LangGraph Persistence  
   https://docs.langchain.com/oss/python/langgraph/persistence

3. LangGraph Memory overview  
   https://docs.langchain.com/oss/python/concepts/memory

4. LangChain Blog, “Context Engineering for Agents”  
   https://www.langchain.com/blog/context-engineering-for-agents

5. LangChain GitHub, `langchain-ai/context_engineering`  
   https://github.com/langchain-ai/context_engineering

6. Anthropic Engineering, “Building effective agents”  
   https://www.anthropic.com/engineering/building-effective-agents

7. Anthropic Engineering, “How we built our multi-agent research system”  
   https://www.anthropic.com/engineering/multi-agent-research-system

8. Drew Breunig, “How Long Contexts Fail”  
   https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html

9. Model Context Protocol Documentation  
   https://modelcontextprotocol.io/introduction

10. HumanLayer, “12-Factor Agents”  
    https://github.com/humanlayer/12-factor-agents

11. 이 저장소의 reference agent 구현  
    `reference_agent/weblog_agent/graph.py`  
    `reference_agent/weblog_agent/state.py`  
    `reference_agent/weblog_agent/prompts.py`  
    `reference_agent/weblog_agent/rag.py`  
    `reference_agent/weblog_agent/tools.py`

---

## 21. 결론

LangChain/LangGraph 에이전트에서 Context Engineering은 다음 네 가지로 압축할 수 있다.

1. **State를 설계하라**  
   컨텍스트를 messages에 쌓지 말고, 구조화된 state로 분리한다.

2. **Node마다 보여줄 컨텍스트를 선택하라**  
   전체 state가 아니라 node별 projection을 LLM에 전달한다.

3. **Tool/RAG/Memory 결과를 압축하고 출처를 유지하라**  
   raw data는 artifact/store에 두고, LLM에는 요약과 source id를 준다.

4. **Graph control flow와 validation으로 모델을 안전하게 제한하라**  
   prompt만 믿지 말고 edge, gate, checkpointer, validator, trace로 운영 가능한 에이전트를 만든다.

즉, LangGraph의 진짜 장점은 “LLM을 그래프에 넣을 수 있다”가 아니라, **LLM이 보는 컨텍스트와 보지 않는 컨텍스트를 상태·노드·엣지·체크포인트 단위로 공학적으로 통제할 수 있다**는 점이다.
