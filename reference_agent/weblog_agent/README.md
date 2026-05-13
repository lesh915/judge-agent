# Web Log Analysis ReAct Reference Agent

Judge Agent가 drift를 탐지/분석/리포팅할 기준 대상(reference target) 에이전트입니다.

이 에이전트는 단순 fixture runner가 아니라, 일반적인 LangChain/LangGraph 기반 AI Agent 구성을 반영합니다.

## Agent 구성

```text
User Request
  -> LangGraph-style graph
      -> initialize_agent
      -> react_agent loop
          Thought -> Action(tool/mcp/rag) -> Observation
      -> validate_findings
      -> finalize report
```

포함 구성요소:

- **LLM**: ReAct action 결정과 최종 리포트 생성
- **Prompt**: system prompt, ReAct protocol, tool policy, output contract
- **Tools**: 로그 로딩/파싱/필터링/메트릭/이상 탐지 도구
- **MCP**: 서비스 소유자, 최근 배포, SLO, dependency metadata 조회
- **RAG**: runbook 검색을 통한 원인 후보/대응 가이드 보강
- **ReAct loop**: `Thought -> Action -> Observation` 반복 후 `finish`
- **Trace**: Judge Agent가 drift를 판단할 수 있도록 모든 LLM/tool/MCP/RAG/edge/state 이벤트 기록

현재 구현은 CI 재현성을 위해 표준 라이브러리 기반으로 동작하지만, trace/graph/prompt/tool interface는 LangChain/LangGraph ReAct Agent 관찰 모델에 맞췄습니다. 실제 LangGraph runtime으로 교체해도 Judge Agent 입력 계약은 유지됩니다.

## LLM configuration

OpenAI-compatible Chat Completions endpoint를 사용합니다.

```bash
export OPENAI_API_KEY=...
export WEBLOG_AGENT_MODEL=gpt-4o-mini
export OPENAI_BASE_URL=https://api.openai.com/v1
```

API key가 없거나 `--no-llm`을 쓰면 deterministic fallback policy로 ReAct action을 선택합니다. 이 경우에도 trace에는 `llm_skipped`가 남습니다.

## Run

```bash
python3 -m reference_agent.weblog_agent.cli list-fixtures
python3 -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike
python3 -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike --no-llm
python3 -m reference_agent.weblog_agent.cli run-all --no-llm
```

Custom analysis:

```bash
python3 -m reference_agent.weblog_agent.cli analyze \
  --input "지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요" \
  --access-log reference_agent/weblog_agent/fixtures/access.log
```

Outputs:

- `reference_agent/weblog_agent/traces/*.jsonl`
- `reference_agent/weblog_agent/reports/*.md`

## ReAct tools

- `parse_user_request`
- `read_log_file`
- `parse_access_log`
- `filter_log_records`
- `compute_log_metrics`
- `detect_log_anomalies`
- `retrieve_runbook` — RAG retriever
- `get_service_context` — MCP-style metadata call
- `collect_evidence`
- `finish`

## Trace events

Judge Agent가 drift를 분석할 때 보는 주요 이벤트:

- `run_start` / `run_end`
- `agent_components`
- `instruction_snapshot`
- `llm_start` / `llm_end` / `llm_error` / `llm_skipped`
- `react_step`
- `observation`
- `node_start` / `node_end`
- `edge_selected`
- `tool_start` / `tool_end` / `tool_error`
- `mcp_start` / `mcp_end` / `mcp_error`
- `validation_result`
- `final_output`

## Drift scenarios covered

Reference fixtures can simulate drift such as:

- prompt/output contract drift
- wrong endpoint/tool input drift
- parse error ignored drift
- validation skipped drift
- metric hallucination drift
- missing/incorrect RAG or MCP context drift, to be expanded

## Optional actual LangGraph app

The CLI runner is dependency-light for CI. If you install optional dependencies, the same nodes can be compiled as an actual LangGraph app:

```bash
pip install -e '.[agent]'
```

See `reference_agent/weblog_agent/langgraph_app.py`:

```python
from reference_agent.weblog_agent.langgraph_app import build_langgraph_app

app = build_langgraph_app(agent)
```

This preserves the same node names and state contract:

```text
initialize_agent -> react_agent -> validate_findings -> finalize -> END
```

## Functional MCP server

MCP is not a mock object. The reference agent starts a real local stdio MCP server:

```bash
python3 -m reference_agent.weblog_agent.mcp_server
```

The agent's `StdioMCPClient` sends JSON-RPC MCP-style messages:

- `initialize`
- `tools/list`
- `tools/call` with `get_service_context`

`get_service_context` returns service metadata used by the report:

- service name
- owner
- recent deployments
- dependencies
- SLO
- runbook references

The trace records this as actual MCP traffic via `mcp_start` / `mcp_end` events for both `tools/list` and `tools/call`.
