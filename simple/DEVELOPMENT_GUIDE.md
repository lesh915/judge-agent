# Simple Development Guide: LangChain/LangGraph Judge Agent

## 0. Reference Agent 구현 반영 사항 (2026-05-14)

개발 우선순위는 기존의 범용 LangSmith adapter 중심에서, 현재 구현된 `reference_agent/weblog_agent` trace를 먼저 분석하는 방식으로 조정한다.

Phase 1에서 반드시 구현할 것:

1. `ReferenceAgentJsonlAdapter`
2. `TraceLogger` JSONL reader
3. WebLog fixture 기반 detector
   - output contract checker
   - wrong endpoint checker
   - metric consistency checker
   - validation node checker
   - parse error handling checker
4. `chat_*` 이벤트를 읽는 최소 chat context checker
5. `python3 -m reference_agent.weblog_agent.cli run-all --no-llm` 산출물을 입력으로 분석하는 CLI

범용 `LangSmithAdapter`는 Phase 1 완료 후 확장한다.

## 1. 개발 목표

LangChain/LangGraph agent의 trace를 입력받아 drift finding을 생성하는 최소 구현을 만든다.

초기 목표:

- Reference Agent JSONL trace 읽기
- `TraceLogger` raw event를 공통 event로 변환
- WebLog fixture 기반 rule checker 5개 이상 구현
- Markdown/JSON report 생성
- 이후 LangGraph/LangChain/LangSmith adapter와 LLM judge를 확장

## 2. 권장 프로젝트 구조

```text
src/
  adapters/
    reference_agent_jsonl_adapter.ts
    langgraph_jsonl_adapter.ts
    langchain_jsonl_adapter.ts
    langsmith_adapter.ts
  schema/
    simple_agent_run.ts
    finding.ts
    metrics.ts
  normalizer/
    trace_builder.ts
    redactor.ts
  metrics/
    tool_metrics.ts
    context_metrics.ts
    graph_metrics.ts
  detectors/
    tool_argument_checker.ts
    tool_error_checker.ts
    node_sequence_checker.ts
    missing_verification_checker.ts
    context_grounding_judge.ts
  judge/
    llm_judge_runner.ts
    prompts.ts
  reports/
    markdown_reporter.ts
    json_reporter.ts
  cli.ts
```

## 3. SimpleAgentRun Schema

```ts
interface SimpleAgentRun {
  runId: string;
  framework: "langchain" | "langgraph";
  agentName?: string;
  agentVersion?: string;
  userInput: string;
  instructions?: {
    system?: string;
    developer?: string;
    toolPolicy?: string;
    memoryPolicy?: string;
  };
  events: SimpleEvent[];
  finalOutput?: string;
  metadata?: Record<string, unknown>;
}
```

## 4. SimpleEvent Schema

```ts
interface SimpleEvent {
  id: string;
  parentId?: string;
  timestamp?: string;
  type:
    | "llm_call"
    | "tool_call"
    | "tool_result"
    | "retrieval"
    | "memory"
    | "graph_node"
    | "graph_edge"
    | "error"
    | "final_output";
  name?: string;
  input?: unknown;
  output?: unknown;
  metadata?: Record<string, unknown>;
}
```

## 5. Adapter 구현

## 5.1 LangSmith Adapter

역할:

- LangSmith run tree export를 읽는다.
- run type에 따라 event로 변환한다.

Mapping:

| LangSmith Run | SimpleEvent |
|---|---|
| llm | `llm_call` |
| chat_model | `llm_call` |
| tool | `tool_call` + `tool_result` |
| retriever | `retrieval` |
| chain | parent event 또는 graph node |
| parser | output validation metadata |

## 5.2 LangChain JSONL Adapter

LangChain callback에서 직접 남긴 JSONL을 읽는다.

권장 callback events:

- `on_chain_start`
- `on_chain_end`
- `on_llm_start`
- `on_llm_end`
- `on_tool_start`
- `on_tool_end`
- `on_retriever_start`
- `on_retriever_end`
- `on_chain_error`

## 5.3 LangGraph JSONL Adapter

LangGraph node/edge/state transition을 직접 기록한 JSONL을 읽는다.

권장 events:

- `node_start`
- `node_end`
- `edge_selected`
- `state_before`
- `state_after`
- `checkpoint_saved`
- `interrupt`
- `human_approval`

## 6. Rule Checker 우선 구현

### 6.1 ToolArgumentChecker

탐지:

- required argument 누락
- type mismatch
- state/context에 없는 값 사용

### 6.2 ToolErrorChecker

탐지:

- tool error 이후 final output이 성공을 주장
- 같은 tool error 반복

### 6.3 RepeatedToolCallChecker

탐지:

- 동일 tool + 동일 argument 반복
- threshold 초과 시 loop finding

### 6.4 NodeSequenceChecker

탐지:

- required node 누락
- 금지된 edge transition
- approval/validation node skip

### 6.5 MissingVerificationChecker

탐지:

- write/edit/action 이후 검증 event 없음
- final output에서 완료를 주장하지만 verification 없음

## 7. LLM Judge 우선 구현

### 7.1 ContextGroundingJudge

입력:

- user input
- retrieved chunks
- final output

출력:

- groundedness score
- unsupported claims
- evidence

### 7.2 InstructionAdherenceJudge

입력:

- instructions
- user input
- trace summary
- final output

출력:

- adherence score
- violation list
- recommendation

## 8. Finding Schema

```ts
interface Finding {
  id: string;
  category: "prompt" | "tool" | "context" | "memory" | "graph" | "completion";
  metric: string;
  severity: "low" | "medium" | "high" | "critical";
  confidence: number;
  evidence: string[];
  expected: string;
  actual: string;
  recommendation: string;
  location?: {
    eventId?: string;
    nodeName?: string;
    toolName?: string;
  };
}
```

## 9. CLI 명령

```bash
judge-agent-simple analyze --trace trace.json --framework langgraph
```

옵션:

- `--trace`: trace 파일
- `--framework`: `langchain` 또는 `langgraph`
- `--output`: markdown report path
- `--json`: findings json path
- `--baseline`: baseline findings path
- `--fail-on`: `medium|high|critical`

## 10. 테스트 Fixture

최소 fixture:

1. wrong tool argument
2. tool error ignored
3. repeated tool loop
4. context contradiction
5. missing verification
6. LangGraph validation node skipped
7. unsupported memory claim

## 11. 구현 순서

### Step 1

- schema 정의
- Reference Agent JSONL reader
- markdown/json reporter

### Step 2

- `ReferenceAgentJsonlAdapter` 구현
- `run_start` / `instruction_snapshot` / `agent_components` / `final_output` 추출
- `tool_*` / `node_*` / `edge_selected` / `validation_result` 정규화

### Step 3

- WebLog fixture 기준 rule checker 5개 구현

### Step 4

- LangGraph/LangChain/LangSmith adapter 확장
- LLM judge 2개 구현

### Step 5

- baseline compare
- CI exit code
- sample fixtures

## 12. 개발 시 주의점

- 처음부터 모든 framework를 지원하지 않는다.
- LangChain/LangGraph trace의 parent-child 관계 복원에 집중한다.
- trace에 없는 내용은 추정하지 않는다.
- evidence 없는 finding은 만들지 않는다.
- privacy를 위해 prompt/context raw text 저장은 옵션화한다.

## Reference Agent 개발 기준 업데이트

reference target은 `reference_agent/weblog_agent`의 Web Log ReAct Agent다.

구현 요구:

- LangGraph-style node/edge event를 기록한다.
- `react_agent` node는 ReAct loop를 수행한다.
- LLM은 `react_decide` call로 다음 action을 결정한다.
- tool/RAG/MCP call은 각각 trace event를 남긴다.
- fallback mode는 CI용이며, fallback도 ReAct step을 동일하게 남긴다.
- final report는 `RAG Context`, `MCP Context`를 포함한다.

로컬 검증:

```bash
python3 -m unittest discover reference_agent/weblog_agent/tests
python3 -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike --no-llm
```
