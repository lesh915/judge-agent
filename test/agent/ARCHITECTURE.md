# Architecture: Web Log Analysis Reference Agent

## 1. 아키텍처 개요

```text
CLI / API / Fixture Runner
          │
          ▼
   LangGraph Workflow
          │
          ├── parse_request
          ├── load_logs ─────── read_log_file
          ├── parse_logs ────── parse_access_log
          ├── filter_logs ───── filter_log_records
          ├── compute_metrics ─ compute_log_metrics
          ├── detect_anomalies  detect_log_anomalies
          ├── collect_evidence
          ├── validate_findings
          └── generate_report
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

## 2.3 Tool Layer

- deterministic log processing tools
- Pydantic input/output schema
- structured errors

## 2.4 State Layer

- WebLogAnalysisState
- state validation
- state redaction for trace

## 2.5 Trace Layer

- JSONL event writer
- event schema
- event correlation
- trace validation

## 2.6 Report Layer

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

초기에는 실제 LLM 호출 의존도를 낮춘다.

- request parsing은 rule-based + optional LLM
- report generation은 template-based + optional LLM
- drift fixture는 static trace 또는 fault injection으로 생성

이렇게 하면 Judge Agent 테스트가 재현 가능하다.
