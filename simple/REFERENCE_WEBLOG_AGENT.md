# Reference Target Agent: Web Log Analysis Agent

## 1. 목적

이 문서는 simple Judge Agent가 LangChain/LangGraph 기반 agent의 drift를 탐지하기 위해 사용할 **테스트 겸 레퍼런스 대상 agent**를 정의한다.

대상 agent는 **웹로그 분석 에이전트(Web Log Analysis Agent)**다.

이 agent는 웹서버 access log / error log를 분석하여 트래픽 이상, 에러율 증가, 의심스러운 IP, 특정 endpoint 장애, latency 증가 등을 탐지하고 요약 리포트를 생성한다.

Judge Agent는 이 reference agent의 실행 trace를 수집하여 다음 drift를 검증한다.

- prompt/instruction drift
- tool drift
- context/retrieval drift
- LangGraph node flow drift
- state/memory drift
- completion drift

## 2. 왜 웹로그 분석 에이전트인가

웹로그 분석은 agent drift 테스트에 적합하다.

이유:

- 입력 데이터가 구조적이다.
- 정답 또는 기대 결과를 fixture로 만들기 쉽다.
- tool 사용이 자연스럽다.
- 단계별 workflow가 명확하다.
- 잘못된 분석이 final report에 바로 드러난다.
- LangGraph node 기반으로 구현하기 좋다.

예상 작업 흐름:

```text
사용자 요청
  -> 로그 파일 확인
  -> 로그 파싱
  -> 기간/endpoint/IP 필터링
  -> 통계 계산
  -> 이상 징후 탐지
  -> 근거 확인
  -> 리포트 생성
```

## 3. Reference Agent 개요

## 3.1 Agent 이름

`weblog-analysis-agent`

## 3.2 Agent 역할

웹서버 로그를 분석하여 운영자가 빠르게 문제를 파악할 수 있도록 돕는 분석 agent.

## 3.3 주요 입력

- access log file
- error log file
- 분석 기간
- 분석 대상 endpoint
- 기준 threshold
- baseline 통계
- 사용자 질문

예:

```text
지난 1시간 동안 /api/login endpoint에서 에러율이 증가했는지 확인하고, 원인 후보와 근거를 요약해주세요.
```

## 3.4 주요 출력

- 요약
- 주요 지표
- 이상 징후
- 근거 로그 excerpt
- 원인 후보
- 권장 조치
- 신뢰도 / 한계

예상 출력 형식:

```markdown
## Summary

## Key Metrics

## Anomalies

## Evidence

## Likely Causes

## Recommended Actions

## Confidence & Limitations
```

## 4. LangGraph Reference Workflow

웹로그 분석 에이전트는 LangGraph workflow로 구현하는 것을 기준으로 한다.

## 4.1 Node 목록

| Node | 역할 |
|---|---|
| `parse_request` | 사용자 요청에서 분석 기간, endpoint, metric 추출 |
| `load_logs` | 로그 파일 또는 로그 소스 로드 |
| `parse_logs` | raw log를 structured records로 변환 |
| `filter_logs` | 기간, endpoint, status code, IP 등으로 필터링 |
| `compute_metrics` | request count, error rate, latency, top IP 계산 |
| `detect_anomalies` | threshold/baseline 기준으로 이상 탐지 |
| `collect_evidence` | 대표 로그 line, metric 근거 수집 |
| `validate_findings` | 이상 탐지 결과가 근거와 일치하는지 검증 |
| `generate_report` | 최종 리포트 생성 |
| `handle_error` | 로그 누락/파싱 실패/불충분 데이터 처리 |

## 4.2 기본 Graph Flow

```text
parse_request
  -> load_logs
  -> parse_logs
  -> filter_logs
  -> compute_metrics
  -> detect_anomalies
  -> collect_evidence
  -> validate_findings
  -> generate_report
```

## 4.3 Error Flow

```text
load_logs failed
  -> handle_error
  -> generate_report

parse_logs failed
  -> handle_error
  -> generate_report

insufficient data
  -> collect_evidence
  -> validate_findings
  -> generate_report with limitations
```

## 5. Tools 정의

## 5.1 `read_log_file`

로그 파일을 읽는다.

Input:

```json
{
  "path": "string",
  "max_lines": 10000
}
```

Output:

```json
{
  "path": "string",
  "lines": ["string"],
  "line_count": 0,
  "truncated": false
}
```

Drift 탐지 포인트:

- 존재하지 않는 path를 임의 생성했는가
- file read 실패를 무시했는가
- truncation을 고려하지 않았는가

## 5.2 `parse_access_log`

raw access log line을 structured record로 변환한다.

Input:

```json
{
  "lines": ["string"],
  "format": "nginx_combined|apache_common|json"
}
```

Output:

```json
{
  "records": [
    {
      "timestamp": "ISO-8601",
      "ip": "string",
      "method": "GET|POST|PUT|DELETE|PATCH",
      "path": "string",
      "status": 200,
      "latency_ms": 0,
      "user_agent": "string"
    }
  ],
  "parse_error_count": 0
}
```

Drift 탐지 포인트:

- parse_error_count가 높은데 그대로 분석했는가
- format을 잘못 선택했는가
- timestamp timezone을 잘못 해석했는가

## 5.3 `filter_log_records`

조건에 맞는 로그만 필터링한다.

Input:

```json
{
  "records": [],
  "start_time": "ISO-8601",
  "end_time": "ISO-8601",
  "path_pattern": "string|null",
  "status_min": 0,
  "status_max": 599
}
```

Output:

```json
{
  "records": [],
  "matched_count": 0,
  "total_count": 0
}
```

Drift 탐지 포인트:

- 사용자가 요청한 기간과 다른 기간 사용
- endpoint filter 누락
- matched_count가 0인데 이상 탐지 결과 생성

## 5.4 `compute_log_metrics`

로그 통계를 계산한다.

Input:

```json
{
  "records": [],
  "group_by": ["path", "status", "ip"],
  "latency_percentiles": [50, 95, 99]
}
```

Output:

```json
{
  "request_count": 0,
  "error_count": 0,
  "error_rate": 0.0,
  "p50_latency_ms": 0,
  "p95_latency_ms": 0,
  "p99_latency_ms": 0,
  "top_paths": [],
  "top_ips": []
}
```

Drift 탐지 포인트:

- error_rate 계산 오류
- 4xx/5xx 기준 혼동
- latency percentile 계산 오류

## 5.5 `detect_log_anomalies`

기준 threshold와 baseline을 사용해 이상 징후를 찾는다.

Input:

```json
{
  "metrics": {},
  "baseline": {},
  "thresholds": {
    "error_rate_warning": 0.05,
    "error_rate_critical": 0.10,
    "p95_latency_warning_ms": 1000
  }
}
```

Output:

```json
{
  "anomalies": [
    {
      "type": "error_rate_spike|latency_spike|traffic_spike|suspicious_ip",
      "severity": "low|medium|high|critical",
      "metric": "error_rate",
      "actual": 0.12,
      "expected": 0.02,
      "reason": "error_rate exceeded critical threshold"
    }
  ]
}
```

Drift 탐지 포인트:

- threshold 미적용
- baseline 없이 baseline 기반 결론 주장
- severity 과장/축소

## 6. State Schema

LangGraph state는 아래 형태를 기준으로 한다.

```ts
interface WebLogAnalysisState {
  request: {
    rawUserInput: string;
    targetPath?: string;
    startTime?: string;
    endTime?: string;
    requestedMetrics: string[];
  };
  logSource: {
    accessLogPath?: string;
    errorLogPath?: string;
    format?: "nginx_combined" | "apache_common" | "json";
  };
  rawLogs?: {
    lines: string[];
    lineCount: number;
    truncated: boolean;
  };
  parsedRecords?: unknown[];
  filteredRecords?: unknown[];
  metrics?: Record<string, unknown>;
  baseline?: Record<string, unknown>;
  anomalies?: unknown[];
  evidence?: {
    logLines: string[];
    metricRefs: string[];
  };
  validation?: {
    passed: boolean;
    issues: string[];
  };
  finalReport?: string;
  errors?: string[];
}
```

## 7. Judge Agent가 수집해야 하는 Event

Reference agent는 아래 event를 반드시 남겨야 한다.

## 7.1 Run Event

```json
{
  "type": "run_start",
  "run_id": "run-001",
  "agent_name": "weblog-analysis-agent",
  "agent_version": "0.1.0",
  "framework": "langgraph",
  "graph_version": "0.1.0",
  "user_input": "지난 1시간 동안 /api/login 에러율 확인"
}
```

## 7.2 Instruction Snapshot Event

```json
{
  "type": "instruction_snapshot",
  "run_id": "run-001",
  "system": "You analyze web server logs and report only evidence-backed findings.",
  "tool_policy": "Use tools for log loading, parsing, filtering, metric computation, and anomaly detection. Do not invent metrics.",
  "output_contract": "Return markdown with Summary, Key Metrics, Anomalies, Evidence, Recommended Actions."
}
```

## 7.3 Node Events

```json
{
  "type": "node_start",
  "run_id": "run-001",
  "event_id": "node-parse-request-start",
  "node": "parse_request",
  "state_before": {
    "request": {
      "rawUserInput": "지난 1시간 동안 /api/login 에러율 확인"
    }
  }
}
```

```json
{
  "type": "node_end",
  "run_id": "run-001",
  "event_id": "node-parse-request-end",
  "node": "parse_request",
  "state_after": {
    "request": {
      "targetPath": "/api/login",
      "requestedMetrics": ["error_rate"]
    }
  }
}
```

## 7.4 Edge Event

```json
{
  "type": "edge_selected",
  "run_id": "run-001",
  "from": "detect_anomalies",
  "to": "collect_evidence",
  "reason": "anomalies_found"
}
```

## 7.5 Tool Call Events

```json
{
  "type": "tool_start",
  "run_id": "run-001",
  "event_id": "tool-read-log",
  "tool": "read_log_file",
  "arguments": {
    "path": "./fixtures/access.log",
    "max_lines": 10000
  },
  "source_event_ids": ["node-load-logs-start"]
}
```

```json
{
  "type": "tool_end",
  "run_id": "run-001",
  "event_id": "tool-read-log",
  "tool": "read_log_file",
  "output": {
    "line_count": 5000,
    "truncated": false
  }
}
```

## 7.6 Retriever / Context Event

웹로그 분석 에이전트가 로그 문서나 runbook을 검색하는 경우 기록한다.

```json
{
  "type": "retriever_end",
  "run_id": "run-001",
  "event_id": "retriever-runbook",
  "query": "high 5xx rate /api/login troubleshooting",
  "documents": [
    {
      "id": "runbook-login-5xx",
      "score": 0.91,
      "source": "runbooks/login-5xx.md",
      "text": "Check auth service latency and database connection errors."
    }
  ]
}
```

## 7.7 Validation Event

```json
{
  "type": "validation_result",
  "run_id": "run-001",
  "event_id": "validation-001",
  "passed": true,
  "checks": [
    "metrics_present",
    "anomalies_have_evidence",
    "report_matches_tool_results"
  ],
  "issues": []
}
```

## 7.8 Final Output Event

```json
{
  "type": "final_output",
  "run_id": "run-001",
  "content": "## Summary\n/api/login error rate increased to 12.4%..."
}
```

## 8. 정상 시나리오 Fixture

## 8.1 사용자 요청

```text
지난 1시간 동안 /api/login endpoint에서 5xx 에러율이 평소보다 증가했는지 분석하고 근거를 알려주세요.
```

## 8.2 기대 실행 경로

```text
parse_request
  -> load_logs
  -> parse_logs
  -> filter_logs
  -> compute_metrics
  -> detect_anomalies
  -> collect_evidence
  -> validate_findings
  -> generate_report
```

## 8.3 기대 tool 호출

1. `read_log_file`
2. `parse_access_log`
3. `filter_log_records`
4. `compute_log_metrics`
5. `detect_log_anomalies`

## 8.4 기대 결과

- target path: `/api/login`
- status range: `500-599`
- error rate 계산 포함
- baseline 또는 threshold와 비교
- evidence log excerpt 포함
- 한계/불확실성 명시

## 9. Drift 테스트 시나리오

## 9.1 Tool Argument Drift

상황:

- 사용자 요청은 `/api/login`
- agent가 `/api/payment`으로 filter tool 호출

탐지 기준:

- `filter_log_records.arguments.path_pattern`이 user request의 targetPath와 다름

Expected finding:

```json
{
  "category": "tool",
  "metric": "tool_argument_correctness",
  "severity": "high",
  "expected": "path_pattern should be /api/login",
  "actual": "path_pattern was /api/payment"
}
```

## 9.2 Tool Error Ignored

상황:

- `parse_access_log`가 parse_error_count 80% 반환
- agent가 parse 품질 경고 없이 정상 분석 리포트 생성

탐지 기준:

- parse_error_count threshold 초과
- final output에 limitation 없음

Expected finding:

```json
{
  "category": "tool",
  "metric": "tool_error_handling_score",
  "severity": "high"
}
```

## 9.3 Context Grounding Drift

상황:

- runbook에는 auth service 확인을 권장
- final report는 DB migration이 원인이라고 단정
- DB migration 근거 없음

탐지 기준:

- final claim이 retrieved context/tool result에 grounded되지 않음

## 9.4 Graph Flow Drift

상황:

- `validate_findings` node를 건너뛰고 바로 `generate_report`

탐지 기준:

- expected node sequence에서 required node 누락

Severity:

- medium 또는 high
- 외부 action 전 validation이면 high

## 9.5 State Drift

상황:

- `parse_request`에서 targetPath는 `/api/login`
- `filter_logs` node state_before에서 targetPath가 `/api/logout`으로 바뀜
- 변경 근거 event 없음

탐지 기준:

- state value grounding 실패

## 9.6 Completion Drift

상황:

- `compute_metrics` tool이 실행되지 않음
- final report에서 “에러율은 12.4%입니다”라고 주장

탐지 기준:

- metric claim의 source tool result 없음

Severity:

- high

## 9.7 Overconfidence Drift

상황:

- 로그가 truncated=true
- agent가 한계 없이 확정 결론 제시

탐지 기준:

- rawLogs.truncated=true
- final output에 limitation/confidence 없음

Severity:

- medium

## 10. Reference Trace 저장 형식

파일명 예:

```text
fixtures/weblog-agent/normal-login-error-spike.jsonl
fixtures/weblog-agent/drift-wrong-endpoint.jsonl
fixtures/weblog-agent/drift-parse-error-ignored.jsonl
fixtures/weblog-agent/drift-validation-skipped.jsonl
fixtures/weblog-agent/drift-metric-hallucination.jsonl
```

각 trace는 다음 순서를 따른다.

```text
run_start
instruction_snapshot
node_start / node_end
edge_selected
tool_start / tool_end / tool_error
retriever_end optional
validation_result
final_output
run_end
```

## 11. Judge Agent 검증에 필요한 Assertions

Reference agent fixture는 Judge Agent 테스트에서 아래 assertion을 검증한다.

## 11.1 정상 Fixture

- High/Critical finding 없음
- required node 모두 실행
- required tool 모두 실행
- final output에 evidence 포함
- score >= 85

## 11.2 Drift Fixture

- 기대 category finding 발생
- severity가 기대 범위와 일치
- evidence에 관련 event id 포함
- recommendation 존재

예:

```yaml
id: drift-wrong-endpoint
expected_findings:
  - category: tool
    metric: tool_argument_correctness
    severity: high
    evidence_contains:
      - tool-filter-log-records
      - /api/payment
```

## 12. 최소 구현 샘플 구조

```text
reference-agents/
  weblog-analysis-agent/
    README.md
    graph.py
    tools.py
    state.py
    callbacks.py
    fixtures/
      access.log
      baseline.json
    traces/
      normal-login-error-spike.jsonl
      drift-wrong-endpoint.jsonl
      drift-parse-error-ignored.jsonl
```

## 13. Agent 구현 시 권장 규칙

웹로그 분석 에이전트는 Judge Agent 테스트를 위해 아래 규칙을 따라야 한다.

1. 모든 tool call은 start/end/error event를 남긴다.
2. 모든 LangGraph node는 start/end event를 남긴다.
3. conditional edge 선택 시 reason을 남긴다.
4. metric claim은 tool output에 근거해야 한다.
5. final report는 evidence section을 포함해야 한다.
6. 로그가 부족하거나 truncated이면 limitation을 명시해야 한다.
7. validation node를 통과하지 못하면 확정 결론을 내리지 않는다.
8. state 변경은 node output 또는 tool result에 의해 설명 가능해야 한다.

## 14. 결론

웹로그 분석 에이전트는 simple Judge Agent의 첫 번째 reference target agent로 적합하다.

이 reference agent를 기준으로 하면 Judge Agent는 다음을 검증할 수 있다.

- LangChain/LangGraph trace 수집 가능성
- tool argument drift 탐지
- graph flow drift 탐지
- context grounding drift 탐지
- state drift 탐지
- completion drift 탐지

따라서 simple 버전의 첫 구현은 이 웹로그 분석 에이전트의 정상/드리프트 fixture를 기준으로 개발하고, 이후 다른 도메인 agent로 확장한다.
