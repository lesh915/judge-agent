# Backend API: Web Log Analysis Reference Agent

## 1. 목적

Backend API는 웹로그 분석 에이전트를 HTTP로 실행하고, 생성된 report와 trace를 조회하기 위한 선택적 인터페이스다.

MVP에서는 CLI가 우선이며, API는 개발/데모/프론트엔드 연동을 위한 보조 기능이다.

## 2. API 개요

Base URL:

```text
http://localhost:8000
```

## 3. Endpoints

## 3.1 Run Analysis

```http
POST /v1/analyze
```

Request:

```json
{
  "user_input": "지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요.",
  "access_log_path": "fixtures/access.log",
  "error_log_path": null,
  "log_format": "nginx_combined",
  "baseline_path": "fixtures/baseline.json",
  "trace": true
}
```

Response:

```json
{
  "run_id": "run-001",
  "status": "completed",
  "report": "## Summary\n...",
  "trace_path": "traces/run-001.jsonl",
  "metrics": {
    "request_count": 1000,
    "error_rate": 0.124
  }
}
```

## 3.2 Run Fixture

```http
POST /v1/fixtures/{fixture_id}/run
```

Response:

```json
{
  "fixture_id": "drift-wrong-endpoint",
  "run_id": "run-002",
  "trace_path": "traces/drift-wrong-endpoint.jsonl",
  "expected_findings_path": "fixtures/expected/drift-wrong-endpoint.yaml"
}
```

## 3.3 List Fixtures

```http
GET /v1/fixtures
```

Response:

```json
{
  "fixtures": [
    {
      "id": "normal-login-error-spike",
      "type": "normal"
    },
    {
      "id": "drift-wrong-endpoint",
      "type": "drift",
      "category": "tool"
    }
  ]
}
```

## 3.4 Get Run

```http
GET /v1/runs/{run_id}
```

Response:

```json
{
  "run_id": "run-001",
  "status": "completed",
  "report_path": "reports/run-001.md",
  "trace_path": "traces/run-001.jsonl"
}
```

## 3.5 Get Trace

```http
GET /v1/runs/{run_id}/trace
```

Response:

```json
{
  "run_id": "run-001",
  "events": []
}
```

## 4. Error Response

```json
{
  "error": {
    "code": "LOG_FILE_NOT_FOUND",
    "message": "access log file not found",
    "details": {}
  }
}
```

## 5. API 구현 우선순위

1. `POST /v1/analyze`
2. `GET /v1/fixtures`
3. `POST /v1/fixtures/{fixture_id}/run`
4. `GET /v1/runs/{run_id}`
5. `GET /v1/runs/{run_id}/trace`
