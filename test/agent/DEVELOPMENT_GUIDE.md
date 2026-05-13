# Development Guide: Web Log Analysis Reference Agent

## 1. 개발 목표

이 문서는 Judge Agent 테스트용 Web Log Analysis Reference Agent를 구현하기 위한 개발 가이드다.

핵심은 기능적으로 로그 분석을 수행하면서, Judge Agent가 drift를 검증할 수 있도록 충분한 trace/event를 남기는 것이다.

## 2. 기술 스택

권장 스택:

- Python 3.11+
- LangGraph
- LangChain Core
- OpenAI-compatible Chat Completions API
- Pydantic
- Typer 또는 Click CLI
- pytest
- JSONL trace logger

MVP 구현은 CI에서 바로 실행 가능하도록 Python 표준 라이브러리 기반 fallback을 제공한다. 단, 실제 agent 동작을 위해 `OPENAI_API_KEY`가 있으면 request parsing과 report generation 단계에서 LLM을 호출해야 한다.

선택:

- FastAPI: API server 구현 시
- React/Vite: 간단한 frontend 구현 시

## 3. 권장 폴더 구조

```text
test/agent/
  PRD.md
  DEVELOPMENT_GUIDE.md
  SYSTEM_DESIGN.md
  ARCHITECTURE.md
  BACKEND_API.md
  FRONTEND.md
  README.md

reference_agent/
  weblog_agent/
    __init__.py
    graph.py
    state.py
    tools.py
    prompts.py
    validation.py
    reporting.py
    trace.py
    fixtures.py
    cli.py
    api.py
    tests/
      test_tools.py
      test_graph.py
      test_fixtures.py
    fixtures/
      access.log
      baseline.json
    traces/
      normal-login-error-spike.jsonl
      drift-prompt-output-contract.jsonl
      drift-wrong-endpoint.jsonl
```

## 4. 구현 순서

### Step 1. State Schema

`WebLogAnalysisState`를 Pydantic model 또는 TypedDict로 정의한다.

필수 field:

- request
- logSource
- rawLogs
- parsedRecords
- filteredRecords
- metrics
- baseline
- anomalies
- evidence
- validation
- finalReport
- errors

### Step 2. Trace Logger

모든 node/tool 실행에서 JSONL event를 남기는 logger를 구현한다.

필수 함수:

- `emit_run_start`
- `emit_instruction_snapshot`
- `emit_node_start`
- `emit_node_end`
- `emit_edge_selected`
- `emit_tool_start`
- `emit_tool_end`
- `emit_tool_error`
- `emit_validation_result`
- `emit_final_output`
- `emit_run_end`

### Step 3. Tools 구현

구현 tool:

1. `read_log_file`
2. `parse_access_log`
3. `filter_log_records`
4. `compute_log_metrics`
5. `detect_log_anomalies`

각 tool은 input/output schema를 명확히 갖고, 실패 시 structured error를 반환한다.

### Step 4. LangGraph Nodes 구현

구현 node:

- `parse_request`
- `load_logs`
- `parse_logs`
- `filter_logs`
- `compute_metrics`
- `detect_anomalies`
- `collect_evidence`
- `validate_findings`
- `generate_report`
- `handle_error`

각 node는 시작/종료 event를 남긴다.

### Step 5. Edge Logic 구현

기본 flow:

```text
parse_request -> load_logs -> parse_logs -> filter_logs -> compute_metrics -> detect_anomalies -> collect_evidence -> validate_findings -> generate_report
```

error flow:

```text
load_logs failed -> handle_error -> generate_report
parse_logs failed -> handle_error -> generate_report
insufficient data -> collect_evidence -> validate_findings -> generate_report
```

### Step 6. LLM 연결

에이전트는 최소 2개 지점에서 LLM을 사용한다.

1. `parse_request`: 사용자 요청을 구조화된 분석 의도로 변환
2. `generate_report`: tool/metric/evidence/state를 기반으로 최종 리포트 작성

요구사항:

- OpenAI-compatible Chat Completions endpoint 지원
- `OPENAI_API_KEY`, `WEBLOG_AGENT_MODEL`, `OPENAI_BASE_URL` 환경변수 지원
- API key가 없으면 deterministic fallback으로 정상 동작
- fallback 사용 시 trace에 `llm_skipped` event 기록
- LLM 호출 시 `llm_start`, `llm_end`, `llm_error` event 기록

### Step 7. Fixture Runner

정상 및 drift fixture를 실행하는 CLI를 만든다.

예:

```bash
python -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike
python -m reference_agent.weblog_agent.cli run-fixture drift-wrong-endpoint
python -m reference_agent.weblog_agent.cli run-all --output traces/
```

### Step 8. Tests

테스트 종류:

- tool unit test
- parser test
- metric calculation test
- graph path test
- trace event schema test
- fixture expected behavior test

## 5. Trace Event 작성 규칙

- 모든 event는 `run_id`를 포함한다.
- node/tool event는 `event_id`를 포함한다.
- tool_start/tool_end/tool_error는 같은 `event_id`를 사용한다.
- state는 민감정보를 제거하거나 allowlist만 기록한다.
- edge_selected에는 reason을 포함한다.
- final_output은 report content를 포함한다.

## 6. Drift Fixture 구현 방식

Drift fixture는 두 방식 중 하나로 구현한다.

### 6.1 Fault Injection 방식

정상 graph 실행 중 특정 node/tool output을 변조한다.

예:

- `filter_logs`에서 targetPath를 `/api/payment`로 변경
- `validate_findings` node skip
- `compute_metrics` tool call 생략

### 6.2 Static Trace 방식

의도적으로 잘못된 JSONL trace를 fixture로 저장한다.

초기 MVP에서는 Static Trace 방식이 빠르다.

## 7. Prompt 작성 규칙

System prompt는 다음을 반드시 포함한다.

- evidence-backed reporting
- do not invent metrics
- report limitations
- use tools for log operations
- follow markdown output contract

## 8. Report 작성 규칙

리포트는 항상 아래 section을 포함한다.

- Summary
- Key Metrics
- Anomalies
- Evidence
- Likely Causes
- Recommended Actions
- Confidence & Limitations

## 9. 품질 기준

- 정상 fixture score가 Judge Agent 기준 85 이상이어야 한다.
- drift fixture는 기대 finding을 유발해야 한다.
- trace schema validation을 통과해야 한다.
- tool output과 final report claim이 연결 가능해야 한다.

## 10. 개발 주의사항

- 레퍼런스 에이전트는 복잡한 기능보다 trace 품질이 중요하다.
- drift fixture는 재현 가능해야 한다.
- LLM의 비결정성을 줄이기 위해 fixture 테스트는 가능하면 deterministic tool output을 사용한다.
- 실제 LLM 호출 없이 static trace로도 Judge Agent 테스트가 가능해야 한다.

## ReAct 구현 지침 추가

구현은 LangChain/LangGraph agent를 모델링해야 한다.

1. `initialize_agent` node에서 구성요소 snapshot을 trace에 기록한다.
2. `react_agent` node에서 ReAct loop를 실행한다.
3. LLM은 매 step JSON으로 다음 action을 반환한다.
4. action은 tool/RAG/MCP/finish 중 하나여야 한다.
5. 각 action 결과는 `observation` event로 기록한다.
6. deterministic fallback은 CI용으로만 사용하고 `llm_skipped`를 남긴다.
7. `validate_findings`에서 metrics/evidence/RAG/MCP/output contract를 검증한다.
8. final report는 RAG/MCP context를 별도 section으로 표시한다.

테스트는 `react_step`, `mcp_start/mcp_end`, RAG tool call, LLM event를 검증해야 한다.

## LLM 환경 설정 관리 지침

LLM endpoint/model/auth 정보는 코드에 하드코딩하지 않는다.

- 기본 예시는 `reference_agent/weblog_agent/.env.example`에 둔다.
- 실제 값은 `reference_agent/weblog_agent/.env` 또는 `WEBLOG_AGENT_ENV_FILE`로 지정한 외부 파일에 둔다.
- OpenAI-compatible URL이면 OpenAI, local LLM, 사내 gateway 모두 동일 client로 호출한다.
- API key가 필요한 경우 `WEBLOG_AGENT_LLM_API_KEY_ENV`로 secret env var 이름만 설정한다.
- local LLM은 `WEBLOG_AGENT_LLM_REQUIRE_API_KEY=false`로 실행한다.
- trace에는 sanitized config만 기록한다.
