# Reference Target Agent: Web Log ReAct Agent

## 1. 목적

Judge Agent가 탐지/분석/리포팅할 대상은 단순 workflow가 아니라 **일반적인 LangChain/LangGraph 기반 AI Agent**다. 따라서 reference target agent도 다음 구성을 갖는 실제 동작 agent여야 한다.

- LLM
- Prompt / instruction set
- Tools
- MCP context
- RAG retriever
- LangGraph-style state graph
- ReAct loop: Thought → Action → Observation → Final
- 실행 trace / state snapshot / validation result

Reference domain은 웹로그 분석이다. 웹서버 access log를 분석해 endpoint별 에러율, latency, 이상 징후, 원인 후보, 권장 조치를 리포팅한다.

## 2. Agent 이름

`weblog-react-agent`

## 3. Agent 구성

```text
User Request
  -> LangGraph StateGraph
      -> initialize_agent
      -> react_agent
          -> LLM decides next action
          -> tool / rag / mcp call
          -> observation appended to state
          -> repeat
      -> validate_findings
      -> finalize
  -> Markdown Report + JSONL Trace
```

## 3.1 LLM

역할:

- 사용자 의도 해석
- 다음 ReAct action 선택
- 관찰 결과 기반 추론
- 최종 리포트 생성

환경변수:

```bash
OPENAI_API_KEY
WEBLOG_AGENT_MODEL
OPENAI_BASE_URL
```

LLM이 없을 때도 fixture/CI를 위해 deterministic fallback policy로 동작한다. 단, trace에는 반드시 `llm_skipped`가 기록된다.

## 3.2 Prompt

Prompt는 drift 탐지 대상이다.

구성:

- `SYSTEM_PROMPT`
- `REACT_PROTOCOL`
- `TOOL_POLICY`
- `OUTPUT_CONTRACT`

Drift 예:

- tool 사용 의무 삭제
- evidence 없이 원인 단정 허용
- output section 누락
- RAG/MCP context를 measured evidence처럼 취급

## 3.3 Tools

Core tools:

| Tool | 역할 |
|---|---|
| `parse_user_request` | targetPath, metric, status focus 추출 |
| `read_log_file` | raw access log 로드 |
| `parse_access_log` | raw line → structured record |
| `filter_log_records` | endpoint/status/time filter |
| `compute_log_metrics` | request_count, error_rate, latency percentile 계산 |
| `detect_log_anomalies` | threshold/baseline 기반 이상 탐지 |
| `collect_evidence` | representative log line / metric ref 수집 |

Tool drift 예:

- 잘못된 endpoint로 필터링
- tool 결과 대신 metric hallucination
- parse error 무시
- tool 실패를 report에 반영하지 않음

## 3.4 RAG

RAG tool:

- `retrieve_runbook`

역할:

- `/api/login` 등 service runbook 검색
- common causes, recommended checks, dependency hints 제공

주의:

- RAG 문서는 원인 후보/대응 가이드일 뿐 measured evidence가 아니다.
- Judge Agent는 RAG context가 누락되거나 잘못 사용되는 drift를 탐지해야 한다.

RAG drift 예:

- 관련 없는 runbook 검색
- retrieved context 무시
- runbook 가설을 확정 원인으로 표현

## 3.5 MCP

MCP-style tool:

- `get_service_context`

역할:

- service name
- owner
- recent deployments
- dependencies
- SLO

MCP drift 예:

- owner/service metadata 누락
- `/api/login` 분석 중 `/api/payment` metadata 사용
- deployment metadata를 로그 근거 없이 root cause로 단정

## 4. ReAct 동작

기본 ReAct 순서:

```text
1. Thought: 사용자 요청 구조화 필요
   Action: parse_user_request
   Observation: targetPath=/api/login, metric=error_rate

2. Thought: 로그 데이터 필요
   Action: read_log_file
   Observation: line_count=100

3. Thought: structured record 필요
   Action: parse_access_log
   Observation: records=100, parse_error_count=0

4. Thought: 대상 endpoint로 scope 필요
   Action: filter_log_records
   Observation: matched_count=80

5. Thought: 정량 지표 필요
   Action: compute_log_metrics
   Observation: error_rate=0.15, p95_latency=1400

6. Thought: 이상 여부 판단 필요
   Action: detect_log_anomalies
   Observation: error_rate_spike, latency_spike

7. Thought: 운영 runbook context 필요
   Action: retrieve_runbook
   Observation: /api/login runbook retrieved

8. Thought: 서비스 metadata 필요
   Action: get_service_context
   Observation: owner=identity-platform, dependencies=...

9. Thought: 리포트 근거 필요
   Action: collect_evidence
   Observation: representative 5xx lines

10. Thought: 충분한 근거 확보
    Action: finish
```

## 5. LangGraph 기준 노드

| Node | 역할 |
|---|---|
| `initialize_agent` | LLM/prompt/tools/MCP/RAG 구성 snapshot |
| `react_agent` | ReAct loop 실행 |
| `validate_findings` | metrics/evidence/RAG/MCP/output contract 검증 |
| `finalize` | 최종 report 확정 |
| `handle_error` | tool/LLM/MCP/RAG 실패 처리 |

## 6. 출력 계약

```markdown
## Summary
## Key Metrics
## Anomalies
## Evidence
## RAG Context
## MCP Context
## Likely Causes
## Recommended Actions
## Confidence & Limitations
```

## 7. Trace 요구사항

Judge Agent 입력 trace는 최소 다음 이벤트를 포함해야 한다.

- `run_start`, `run_end`
- `agent_components`
- `instruction_snapshot`
- `llm_start`, `llm_end`, `llm_error`, `llm_skipped`
- `react_step`
- `observation`
- `node_start`, `node_end`
- `edge_selected`
- `tool_start`, `tool_end`, `tool_error`
- `mcp_start`, `mcp_end`, `mcp_error`
- `validation_result`
- `final_output`

## 8. Judge Agent가 탐지해야 할 drift

| Drift | 탐지 예 |
|---|---|
| Prompt drift | output contract section 누락, tool policy 약화 |
| ReAct drift | tool 없이 final 생성, observation 없는 reasoning |
| Tool drift | wrong endpoint, metric hallucination |
| RAG drift | 관련 없는 문서 사용, runbook 가설 단정 |
| MCP drift | 잘못된 service metadata 사용 |
| State drift | 이전 observation 무시, filteredRecords와 metrics 불일치 |
| Validation drift | evidence/metric mismatch를 통과 |
| Report drift | limitation 누락, unsupported cause 단정 |

## 9. 현재 구현 위치

```text
reference_agent/weblog_agent/
  graph.py       # LangGraph-style ReAct agent
  llm.py         # OpenAI-compatible LLM client
  prompts.py     # system/react/tool/output prompts
  tools.py       # deterministic log tools
  rag.py         # local runbook retriever
  mcp.py         # mock MCP service context client
  state.py       # agent state
  trace.py       # JSONL trace logger
```
