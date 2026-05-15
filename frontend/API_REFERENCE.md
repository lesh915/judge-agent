# Judge Agent Frontend API Reference

Base URL for local development:

```text
http://localhost:8787
```

Frontend environment variable:

```bash
VITE_JUDGE_API_BASE_URL=http://localhost:8787
```

This API connects three runtimes:

1. Reference Web Log ReAct Agent — produces trace/report artifacts.
2. Simple Judge Agent analyzer — converts traces into findings, scores, and gates.
3. Conversational Judge Agent — answers follow-up questions over analysis state.

## Conventions

- All request and response bodies are JSON unless noted.
- Timestamps are Unix seconds in MVP responses.
- File paths are returned as strings and are restricted to repository/artifact locations by backend policy.
- Secrets are never returned. LLM credentials are represented only by `configured` flags.
- Long-running jobs are synchronous in MVP, but resources already expose `status` so background execution can be added later.

## Error Response

```json
{
  "error": {
    "code": "TRACE_NOT_FOUND",
    "message": "Trace file not found",
    "detail": {"tracePath": "..."}
  }
}
```

Common codes:

| Code | Meaning |
| --- | --- |
| `BAD_REQUEST` | Invalid request payload |
| `REFERENCE_FIXTURE_NOT_FOUND` | Unknown reference fixture id |
| `REFERENCE_RUN_FAILED` | Reference agent execution failed |
| `REFERENCE_RUN_NOT_FOUND` | Run id does not exist in registry |
| `TRACE_NOT_FOUND` | Trace artifact does not exist |
| `ANALYSIS_FAILED` | Judge analysis failed |
| `ANALYSIS_NOT_FOUND` | Analysis id does not exist |
| `SESSION_NOT_FOUND` | Judge session id does not exist |
| `LLM_UNAVAILABLE` | Requested LLM provider is unavailable |

## GET `/api/health`

Returns backend health.

Response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "runtime": "file-backed"
}
```

## GET `/api/config`

Returns API-safe runtime configuration.

Response:

```json
{
  "configDir": "simple/config",
  "appDefaults": {
    "adapter": "reference-weblog-jsonl",
    "sessionDir": "artifacts/simple-judge/sessions",
    "chatMode": "deterministic",
    "failOn": "critical"
  },
  "supported": {
    "chatModes": ["deterministic", "deterministic-v2", "hybrid", "graph"],
    "llmProviders": ["auto", "openai", "ollama", "mock", "none"]
  },
  "llmProfiles": {
    "defaultProvider": "auto",
    "defaultModel": "gpt-4o-mini"
  },
  "metrics": {"count": 35}
}
```

## GET `/api/metrics`

Returns drift metric registry metadata.

Response:

```json
{
  "metrics": [
    {
      "name": "validation_path_coverage",
      "category": "LangGraph Flow",
      "severity": "Critical",
      "measurement_method": "rule (expected path)",
      "value_type": "pass/fail",
      "description": "...",
      "mvp_priority": null,
      "ref_agent_priority": 4
    }
  ]
}
```

## GET `/api/reference/fixtures`

Lists executable Reference Agent fixtures.

Response:

```json
{
  "fixtures": [
    {
      "id": "normal-login-error-spike",
      "userInput": "지난 1시간 동안 /api/login endpoint...",
      "accessLogPath": "reference_agent/weblog_agent/fixtures/access.log",
      "fault": null,
      "expectedCategory": null
    }
  ]
}
```

## POST `/api/reference/runs`

Runs the Reference Agent and stores generated artifacts.

### Fixture request

```json
{
  "mode": "fixture",
  "fixtureId": "normal-login-error-spike",
  "useLlm": false
}
```

### Custom analysis request

```json
{
  "mode": "custom-analysis",
  "userInput": "지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요",
  "accessLogPath": "reference_agent/weblog_agent/fixtures/access.log",
  "useLlm": false
}
```

Response:

```json
{
  "run": {
    "id": "ref_1715780000_normal-login-error-spike",
    "mode": "fixture",
    "status": "succeeded",
    "fixtureId": "normal-login-error-spike",
    "useLlm": false,
    "tracePath": "artifacts/frontend-api/reference-runs/traces/normal-login-error-spike.jsonl",
    "reportPath": "artifacts/frontend-api/reference-runs/reports/normal-login-error-spike.md",
    "eventCounts": {
      "run_start": 1,
      "react_step": 9,
      "validation_result": 1,
      "final_output": 1
    },
    "timelinePreview": [
      {
        "index": 10,
        "type": "react_step",
        "title": "compute_log_metrics",
        "detail": "..."
      }
    ],
    "createdAt": 1715780000.0,
    "updatedAt": 1715780002.0
  }
}
```

## GET `/api/reference/runs`

Lists stored Reference Agent runs.

Response:

```json
{"runs": [{"id": "ref_...", "status": "succeeded"}]}
```

## GET `/api/reference/runs/{run_id}`

Returns run metadata and report excerpt.

Response:

```json
{
  "run": {"id": "ref_...", "tracePath": "..."},
  "reportExcerpt": "## Summary\n..."
}
```

## GET `/api/reference/runs/{run_id}/trace`

Returns parsed JSONL trace events.

Query parameters:

| Name | Default | Meaning |
| --- | --- | --- |
| `offset` | `0` | first event index |
| `limit` | `200` | maximum event count |
| `type` | none | optional event type filter |

Response:

```json
{
  "runId": "ref_...",
  "tracePath": "...jsonl",
  "events": [
    {"index": 0, "type": "run_start", "raw": {}}
  ],
  "nextOffset": 200
}
```

## POST `/api/analyses`

Analyzes trace paths or a Reference Agent run trace.

### Trace paths request

```json
{
  "source": {
    "kind": "trace-paths",
    "tracePaths": ["artifacts/frontend-api/reference-runs/traces/normal-login-error-spike.jsonl"]
  },
  "adapter": "reference-weblog-jsonl"
}
```

### Reference run request

```json
{
  "source": {
    "kind": "reference-run",
    "referenceRunId": "ref_1715780000_normal-login-error-spike"
  },
  "adapter": "reference-weblog-jsonl"
}
```

Response:

```json
{
  "analysis": {
    "id": "ana_1715780003",
    "status": "succeeded",
    "source": {"kind": "reference-run", "tracePaths": ["...jsonl"]},
    "summary": {
      "runCount": 1,
      "gateCounts": {"pass": 0, "warning": 0, "block": 1},
      "severityCounts": {"low": 0, "medium": 0, "high": 1, "critical": 1},
      "topFindings": []
    },
    "findings": []
  }
}
```

## GET `/api/analyses`

Lists analyses.

Response:

```json
{"analyses": [{"id": "ana_...", "status": "succeeded"}]}
```

## GET `/api/analyses/{analysis_id}`

Returns analysis detail and markdown report excerpt.

## POST `/api/judge/sessions`

Creates a conversational Judge Agent session from an analysis.

Request:

```json
{
  "analysisId": "ana_1715780003",
  "sessionId": "weblog-drift-review",
  "mode": "deterministic-v2",
  "llm": {"provider": "none", "model": null}
}
```

Response:

```json
{
  "session": {
    "id": "weblog-drift-review",
    "mode": "deterministic-v2",
    "analysisId": "ana_1715780003",
    "loadedTraces": ["...jsonl"],
    "focus": {"findingId": "JD-001", "metric": "validation_path_coverage"},
    "messages": []
  }
}
```

## GET `/api/judge/sessions`

Lists conversation sessions.

## GET `/api/judge/sessions/{session_id}`

Returns session detail.

## POST `/api/judge/sessions/{session_id}/messages`

Sends a user message to the selected conversational Judge runtime.

Request:

```json
{
  "content": "왜 block이야?",
  "context": {
    "findingId": "JD-001",
    "metric": "validation_path_coverage"
  }
}
```

Response:

```json
{
  "message": {
    "id": "msg_1715780004",
    "role": "assistant",
    "content": "block의 직접 원인은 critical finding...",
    "focusedFindingId": "JD-001",
    "focusedMetric": "validation_path_coverage",
    "toolCalls": [
      {"name": "explain_gate", "status": "success", "summary": "block 1개"}
    ]
  },
  "session": {"id": "weblog-drift-review"}
}
```

## MVP Endpoint Priority

1. `GET /api/health`
2. `GET /api/config`
3. `GET /api/reference/fixtures`
4. `POST /api/reference/runs` fixture mode
5. `POST /api/analyses`
6. `POST /api/judge/sessions`
7. `POST /api/judge/sessions/{session_id}/messages`
