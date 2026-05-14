# Simple 개발 전 Reference Agent 구현 반영 사항

작성일: 2026-05-14

이 문서는 `simple/` 버전 개발을 시작하기 전에, 이미 구현된 테스트/레퍼런스 에이전트(`reference_agent/weblog_agent`)의 실제 내용을 Simple Judge Agent 문서와 개발 계획에 반영하기 위한 변경사항을 정리한다.

## 1. 결론 요약

기존 `simple/` 문서들은 LangSmith/LangChain/LangGraph trace를 일반적으로 지원하는 Judge Agent를 전제로 작성되었다. 그러나 실제 개발 전 기준점으로 사용할 reference agent가 먼저 구현되었으므로, Simple MVP의 1차 대상은 다음으로 조정한다.

```text
1순위 입력: reference_agent/weblog_agent가 생성하는 canonical JSONL trace
2순위 입력: LangGraph custom JSONL
3순위 입력: LangChain callback JSONL
4순위 입력: LangSmith export JSON
```

즉, Simple 개발은 추상적인 LangSmith adapter부터 시작하지 않고, **현재 repo 안에서 재현 가능한 WebLog Reference Agent trace를 먼저 정상 분석**하는 것부터 시작한다.

---

## 2. 현재 구현된 Reference Agent

위치:

```text
reference_agent/weblog_agent/
```

주요 파일:

| 파일 | 역할 |
|---|---|
| `cli.py` | `run-fixture`, `run-all`, `analyze`, `chat`, `list-sessions` CLI entrypoint |
| `graph.py` | LangGraph-style ReAct 단발 분석 agent |
| `chat_agent.py` | 대화형 세션 wrapper, follow-up context 처리 |
| `session.py` | chat session 저장/복원 |
| `trace.py` | drift telemetry JSONL sink, redaction, node/tool helper |
| `state.py` | 분석 state와 snapshot schema |
| `tools.py` | log read/parse/filter/metric/anomaly deterministic tools |
| `rag.py` | local runbook retriever |
| `mcp.py` / `mcp_server.py` | local stdio MCP client/server |
| `validation.py` | final report/state validation |
| `prompts.py` | system/react/tool/output prompt bundle |
| `fixtures.py` | normal/drift fixture 정의 |

---

## 3. 실제 실행 명령

단발 fixture:

```bash
python3 -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike --no-llm
```

전체 fixture:

```bash
python3 -m reference_agent.weblog_agent.cli run-all --no-llm
```

사용자 지정 단발 분석:

```bash
python3 -m reference_agent.weblog_agent.cli analyze \
  --input "지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요" \
  --access-log reference_agent/weblog_agent/fixtures/access.log \
  --no-llm
```

대화형 세션:

```bash
python3 -m reference_agent.weblog_agent.cli chat \
  --access-log reference_agent/weblog_agent/fixtures/access.log \
  --session-id login-incident \
  --no-llm
```

테스트:

```bash
python3 -m unittest discover -s reference_agent/weblog_agent/tests
```

---

## 4. 실제 생성 artifact

| Artifact | 위치 | 설명 |
|---|---|---|
| 단발 trace | `reference_agent/weblog_agent/traces/*.jsonl` | ReAct run telemetry |
| 단발 report | `reference_agent/weblog_agent/reports/*.md` | 최종 markdown report |
| chat trace | `reference_agent/weblog_agent/traces/*-chat.jsonl` | chat session/turn telemetry |
| chat child run trace | `reference_agent/weblog_agent/traces/*-turn-N.jsonl` | chat 중 호출된 단발 ReAct 분석 trace |
| chat session state | `reference_agent/weblog_agent/sessions/*.json` | bounded conversation state |

Simple Judge Agent는 우선 위 artifact를 입력으로 받아야 한다.

---

## 5. 실제 JSONL event 목록

### 5.1 공통/run lifecycle

- `run_start`
- `run_end`
- `final_output`
- `instruction_snapshot`
- `agent_components`

### 5.2 Graph/ReAct

- `node_start`
- `node_end`
- `edge_selected`
- `react_step`
- `observation`

### 5.3 Tool/RAG/MCP/LLM

- `tool_start`
- `tool_end`
- `tool_error`
- `mcp_start`
- `mcp_end`
- `mcp_error`
- `llm_start`
- `llm_end`
- `llm_error`
- `llm_skipped`

RAG는 별도 event가 아니라 `retrieve_runbook` tool의 `tool_start/tool_end`로 기록된다.

### 5.4 Validation

- `validation_result`

### 5.5 Chat mode

- `chat_session_start`
- `chat_session_end`
- `chat_turn_start`
- `chat_turn_end`
- `chat_intent_classified`
- `chat_context_built`
- `chat_analysis_invoked`
- `chat_response_generated`

---

## 6. Fixture 기준 drift 시나리오

| fixture | fault | category | Simple detector 우선순위 |
|---|---|---|---|
| `normal-login-error-spike` | 없음 | baseline | 정상 기준 |
| `drift-prompt-output-contract` | `prompt_output_contract` | prompt/completion | output section 누락 탐지 |
| `drift-wrong-endpoint` | `wrong_endpoint` | tool | user target과 filter/top_paths 불일치 탐지 |
| `drift-parse-error-ignored` | `parse_error_ignored` | tool/validation | parse error 무시 탐지 |
| `drift-validation-skipped` | `validation_skipped` | graph | validation node skip 탐지 |
| `drift-metric-hallucination` | `metric_hallucination` | completion/tool | computed metric과 report claim 불일치 탐지 |

Simple MVP detector는 이 fixture들을 먼저 통과 대상으로 삼는다.

---

## 7. Simple 개발 우선순위 변경

기존 문서의 우선순위는 LangSmithAdapter가 1순위였지만, 실제 구현된 reference agent를 기준으로 다음 순서로 변경한다.

### Phase 1: Reference JSONL 기반 MVP

1. `ReferenceAgentJsonlAdapter` 구현
2. `TraceLogger` JSONL event 읽기
3. `run_start`, `instruction_snapshot`, `agent_components`, `final_output` 추출
4. `tool_start/tool_end`, `node_start/node_end`, `edge_selected`, `validation_result` 정규화
5. Markdown/JSON report 생성
6. fixture별 rule checker 동작

### Phase 2: Drift rule checker

1. `OutputContractChecker`
2. `WrongEndpointChecker`
3. `MetricConsistencyChecker`
4. `ValidationNodeChecker`
5. `ParseErrorHandlingChecker`
6. `RagMcpContextPresenceChecker`
7. `ChatContextDriftChecker`

### Phase 3: Generic LangGraph/LangChain 확장

1. `LangGraphJsonlAdapter`
2. `LangChainJsonlAdapter`
3. `LangSmithAdapter`

---

## 8. SimpleAgentRun schema 반영 사항

기존 schema에 다음 필드를 명시적으로 반영한다.

```ts
interface SimpleAgentRun {
  runId: string;
  sessionId?: string;
  framework: "reference-weblog" | "langchain" | "langgraph" | "langsmith";
  architecture?: "react" | "chat" | "workflow";
  agentName?: string;
  agentVersion?: string;
  graphVersion?: string;
  userInput?: string;
  instructions?: {
    system?: string;
    reactProtocol?: string;
    toolPolicy?: string;
    outputContract?: string;
  };
  components?: {
    llm?: unknown;
    tools?: string[];
    mcpServers?: string[];
    rag?: unknown;
  };
  events: SimpleEvent[];
  validationResults: unknown[];
  finalOutput?: string;
  artifacts?: {
    tracePath?: string;
    reportPath?: string;
    sessionPath?: string;
  };
  metadata?: Record<string, unknown>;
}
```

---

## 9. 문서별 반영 방향

| 문서 | 반영 내용 |
|---|---|
| `PRD.md` | MVP 1차 입력을 Reference JSONL로 조정, chat trace 포함 |
| `ARCHITECTURE.md` | `ReferenceAgentJsonlAdapter`와 actual event mapping 추가 |
| `DEVELOPMENT_GUIDE.md` | Phase 1을 reference trace parser/checker 중심으로 재정렬 |
| `AGENT_INTEGRATION_GUIDE.md` | 다른 agent 이식 전 reference telemetry contract를 기준으로 설명 |
| `DRIFT_METRICS.md` | 실제 fixture 기반 checker/metric 우선순위 추가 |
| `DEVOPS_CICD_SCENARIOS.md` | GitHub Actions 예시를 실제 명령으로 교체/보강 |
| `REFERENCE_WEBLOG_AGENT.md` | chat mode, session, actual env, telemetry guide 반영 |

---

## 10. 관련 상세 문서

Telemetry 코드 위치와 다른 agent 이식 방법은 다음 문서가 기준이다.

```text
docs/DRIFT_TELEMETRY_INTEGRATION_GUIDE.md
```

Simple 문서에서 drift 데이터 전송/수집을 설명할 때는 위 문서를 canonical source로 참조한다.
