# System Design: Web Log Analysis Reference Agent

## 1. 시스템 목적

Web Log Analysis Reference Agent는 웹로그 분석 기능과 Judge Agent 테스트용 trace 생성을 동시에 수행하는 시스템이다.

주요 목적:

- 로그 분석 workflow 제공
- 정상/드리프트 실행 trace 생성
- Judge Agent detector 검증용 fixture 제공
- CI/CD에서 반복 가능한 agent behavior test 제공

## 2. 시스템 경계

### 내부 구성

- CLI runner
- LangGraph workflow
- LLM client for intent extraction and report generation
- log analysis tools
- trace logger
- fixture manager
- optional API server
- optional frontend viewer

### 외부 시스템

- Judge Agent
- GitHub Actions 또는 CI runner
- LangSmith optional
- local filesystem

## 3. 주요 데이터 흐름

```text
User/Fixture Input
  -> CLI/API
  -> LangGraph Workflow
  -> Tools
  -> State Updates
  -> Trace Logger
  -> Final Report
  -> Judge Agent Analysis
```

## 4. 실행 모드

### 4.1 Fixture Mode

정해진 fixture를 실행하고 trace를 생성한다.

### 4.2 Interactive CLI Mode

사용자가 질문과 log path를 전달하면 분석한다.

### 4.3 API Mode

HTTP API로 분석 요청을 받고 report/trace를 반환한다.

### 4.4 Static Trace Mode

미리 작성된 drift trace를 Judge Agent 테스트에 사용한다.

## 5. 주요 서브시스템

## 5.1 Workflow Engine

LangGraph로 구성된다.

역할:

- node orchestration
- conditional edge 처리
- state propagation
- error flow 처리

## 5.2 LLM Layer

LLM Layer는 사용자 요청을 구조화하고 최종 리포트를 생성한다. OpenAI-compatible API를 사용하며, API key가 없으면 fallback logic으로 동작한다. 모든 LLM 사용/미사용은 trace event로 기록한다.

## 5.3 Tool Layer

로그 분석을 위한 deterministic function layer다.

역할:

- file read
- log parsing
- filtering
- metric calculation
- anomaly detection

## 5.4 Trace Layer

Judge Agent가 사용할 event를 JSONL로 저장한다.

역할:

- event emission
- schema validation
- redaction
- trace file write

## 5.5 Fixture Layer

정상/드리프트 시나리오를 관리한다.

역할:

- fixture metadata
- input log file 관리
- expected findings 정의
- run orchestration

## 5.6 Report Layer

최종 분석 리포트를 생성한다.

역할:

- markdown generation
- evidence insertion
- limitation statement

## 6. 저장 데이터

```text
fixtures/
  access.log
  baseline.json
  scenarios/*.yaml
traces/
  *.jsonl
reports/
  *.md
outputs/
  metrics.json
```

## 7. 장애 처리

| 장애 | 처리 |
|---|---|
| 로그 파일 없음 | handle_error -> limitation report |
| parse error 높음 | anomaly 또는 limitation으로 보고 |
| 필터 결과 없음 | insufficient data report |
| metric 계산 실패 | error event 기록 |
| validation 실패 | report에 warning 포함 |

## 8. 보안/프라이버시

- 로그 line은 fixture용 sample만 사용한다.
- IP는 test IP 또는 masked IP 사용을 권장한다.
- secret/token query string은 redaction한다.
- raw state 전체 저장 대신 allowlist 사용.

## ReAct / MCP / RAG 설계 업데이트

Reference agent는 다음 runtime layer를 갖는다.

- **Graph Layer**: LangGraph-style node/edge execution
- **ReAct Controller**: LLM이 next action 결정
- **Tool Layer**: log analysis tools
- **RAG Layer**: runbook retrieval
- **MCP Layer**: service metadata lookup
- **Validation Layer**: tool result/report consistency 검증
- **Trace Layer**: Judge Agent 분석용 JSONL event stream

MCP/RAG 결과는 final answer의 근거와 구분해야 한다. 로그 metric은 measured evidence이고, RAG/MCP는 context/hypothesis/routing metadata다.
