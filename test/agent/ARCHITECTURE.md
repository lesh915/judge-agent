# Architecture: Web Log Analysis Reference Agent

## 1. 아키텍처 개요

```text
CLI / API / Fixture Runner
          │
          ▼
   LangGraph Workflow
          │
          ├── parse_request ─── LLM intent extraction + fallback parser
          ├── load_logs ─────── read_log_file
          ├── parse_logs ────── parse_access_log
          ├── filter_logs ───── filter_log_records
          ├── compute_metrics ─ compute_log_metrics
          ├── detect_anomalies  detect_log_anomalies
          ├── collect_evidence
          ├── validate_findings
          └── generate_report ─ LLM report synthesis + template fallback
          │
          ▼
   Trace Logger(JSONL)
          │
          ▼
   Judge Agent Input
```

## 2. Layer 구성

## 2.1 Interface Layer

- CLI
- optional FastAPI
- fixture runner

## 2.2 Workflow Layer

- LangGraph graph definition
- node functions
- edge routing
- error handling

## 2.3 LLM Layer

- OpenAI-compatible Chat Completions client
- request intent extraction
- final report synthesis
- `llm_start` / `llm_end` / `llm_error` / `llm_skipped` trace events
- deterministic fallback when API key is missing

## 2.4 Tool Layer

- deterministic log processing tools
- Pydantic input/output schema
- structured errors

## 2.5 State Layer

- WebLogAnalysisState
- state validation
- state redaction for trace

## 2.6 Trace Layer

- JSONL event writer
- event schema
- event correlation
- trace validation

## 2.7 Report Layer

- markdown report builder
- evidence formatting
- confidence/limitations formatter

## 3. LangGraph Node Detail

| Node | Input | Output |
|---|---|---|
| parse_request | raw user input | request fields |
| load_logs | logSource | rawLogs |
| parse_logs | rawLogs | parsedRecords |
| filter_logs | parsedRecords + request | filteredRecords |
| compute_metrics | filteredRecords | metrics |
| detect_anomalies | metrics + baseline | anomalies |
| collect_evidence | anomalies + records | evidence |
| validate_findings | metrics/anomalies/evidence | validation |
| generate_report | full state | finalReport |
| handle_error | errors | limitation report state |

## 4. Trace Emission Points

- run start/end
- instruction snapshot
- before/after each node
- before/after each tool
- edge selection
- validation result
- final output

## 5. Drift Fixture Architecture

```text
Scenario YAML
  -> Fixture Runner
  -> Normal Graph or Fault Injection
  -> Trace JSONL
  -> Expected Findings YAML
  -> Judge Agent Test
```

## 6. MVP 구현 방식

MVP도 실제 LLM 연결을 지원한다. 다만 CI와 fixture 재현성을 위해 fallback 경로를 함께 제공한다.

- 기본 실행: LLM 기반 request parsing + LLM 기반 report generation
- API key 없음: deterministic fallback + `llm_skipped` trace
- CI fixture: `--no-llm` 옵션으로 deterministic 실행 가능
- drift fixture: static trace 또는 fault injection으로 생성

이렇게 하면 실제 에이전트처럼 동작하면서도 Judge Agent 테스트는 재현 가능하다.

## 7. ReAct Agent Architecture Update

Reference implementation은 아래 구조를 따른다.

```text
initialize_agent
  -> react_agent
      -> LLM react_decide
      -> action: tool | retriever | MCP | finish
      -> observation
      -> loop
  -> validate_findings
  -> finalize
```

Agent component registry:

- LLM client: OpenAI-compatible chat model
- Prompt bundle: `SYSTEM_PROMPT`, `REACT_PROTOCOL`, `TOOL_POLICY`, `OUTPUT_CONTRACT`
- Tools: deterministic log analysis tools
- RAG: `LocalRunbookRetriever`
- MCP: `StdioMCPClient` + local `mcp_server.py` exposing `initialize`, `tools/list`, and `tools/call`

Judge Agent는 이 trajectory를 drift 분석 대상으로 삼는다.
