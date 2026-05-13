# Judge Agent 시스템 아키텍처

## 1. 목적

이 문서는 Judge Agent가 agent drift를 탐지하기 위해 필요한 전체 시스템 아키텍처를 정의한다.

범위는 다음을 포함한다.

- 수집(Collection)
- 정규화(Normalization)
- 측정(Measurement)
- 탐지(Detection)
- 분석(Analysis)
- 알림(Alerting)
- 리포팅(Reporting)
- 외부 agent / observability / CI / 운영 시스템과의 연동

Judge Agent는 특정 agent framework에 종속되지 않고, 다양한 agent 구현체에서 생성되는 trace, log, telemetry, memory, tool execution 정보를 표준 schema로 변환한 뒤 drift를 평가한다.

## 2. 전체 아키텍처 개요

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Runtime Layer                         │
│                                                                     │
│  LangGraph  OpenAI Agents  CrewAI  AutoGen  LlamaIndex  Custom      │
│      │          │             │       │        │          │          │
│      └──────────┴─────────────┴───────┴────────┴──────────┘          │
│                         Trace / Event Emitters                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Integration / Ingestion Layer                   │
│                                                                     │
│  Framework Adapters │ OTel Collector │ JSONL Import │ API Webhook   │
│  Proxy/Gateway Logs │ Observability Platform Exporters              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Normalization Layer                           │
│                                                                     │
│  Schema Mapper │ Redactor │ Trace Builder │ Event Correlator         │
│  Missing Observability Detector │ Run Validator                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Measurement Layer                             │
│                                                                     │
│  Prompt Metrics │ Tool Metrics │ Context Metrics │ Memory Metrics    │
│  Reasoning Metrics │ Safety Metrics │ Output Quality Metrics        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Detection Layer                              │
│                                                                     │
│  Rule Checkers │ LLM Judges │ Baseline Comparator │ Trace Analyzer    │
│  Regression Detector │ Policy Checker                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Analysis Layer                              │
│                                                                     │
│  Finding Aggregator │ Severity Scorer │ Root Cause Analyzer          │
│  Impact Analyzer │ Remediation Generator │ Fixture Generator         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Notification / Reporting Layer                   │
│                                                                     │
│  Markdown Report │ JSON Findings │ CI Gate │ PR Comment              │
│  Slack/Discord/Webhook Alert │ Dashboard Export │ Trend Reports      │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. 핵심 설계 원칙

### 3.1 Framework-agnostic

Judge Agent는 LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, LlamaIndex, PydanticAI, Semantic Kernel, Mastra, Vercel AI SDK, MCP 기반 agent, 자체 구현 agent를 모두 수용할 수 있어야 한다.

이를 위해 framework별 trace를 직접 분석하지 않고, 먼저 `NormalizedAgentRun`으로 변환한다.

### 3.2 Trace-first

Agent drift는 최종 응답만으로는 충분히 탐지할 수 없다.

필수 관측 대상:

- prompt / instruction snapshot
- LLM call
- tool call / result / error
- context retrieval
- memory read / write / update
- plan / step / state transition
- guardrail / approval
- handoff / routing
- final response

### 3.3 Rule-first, Judge-second

결정적으로 판정 가능한 항목은 rule checker가 먼저 처리한다.

예:

- schema violation
- required approval missing
- tool argument type mismatch
- duplicate loop
- output format violation

LLM judge는 개방형 판단이 필요한 항목에 사용한다.

예:

- plan quality
- persona consistency
- root cause hypothesis
- answer helpfulness
- goal alignment

### 3.4 Evidence-required

모든 finding은 evidence를 가져야 한다.

허용 evidence:

- message excerpt
- tool call id
- memory operation id
- retrieved context chunk id
- trace span id
- file path / diff
- policy rule id

근거가 부족하면 finding이 아니라 `hypothesis` 또는 `observability_gap`으로 분류한다.

### 3.5 Privacy-by-design

Trace에는 민감정보가 포함될 수 있으므로 기본적으로 redaction과 최소 수집 원칙을 적용한다.

- raw prompt 저장은 opt-in
- memory snapshot 전체 저장 금지, referenced memory 우선
- secret/token/key 자동 마스킹
- 외부 LLM judge 사용 시 전송 범위 표시
- report export 전 privacy scan 수행

## 4. 주요 시스템 컴포넌트

## 4.1 Agent Runtime Layer

실제 업무를 수행하는 외부 agent 시스템이다.

예:

- LangGraph workflow agent
- OpenAI Agents SDK multi-agent
- CrewAI crew/task agent
- AutoGen group chat agent
- LlamaIndex RAG agent
- MCP tool-using coding agent
- 자체 구현 Python/TypeScript agent

### 역할

- 사용자 요청 처리
- LLM 호출
- tool 사용
- memory/context 사용
- workflow 실행
- trace/event 생성

### Judge Agent와의 계약

Agent Runtime은 최소한 다음 중 하나를 제공해야 한다.

- OpenTelemetry trace
- framework-native trace export
- structured JSONL log
- observability platform trace id
- webhook event stream
- batch run artifact

## 4.2 Integration / Ingestion Layer

외부 agent의 실행 데이터를 Judge Agent로 가져오는 계층이다.

### 입력 방식

| 방식 | 설명 | 적합한 경우 |
|---|---|---|
| Framework Adapter | LangSmith, OpenAI Agents, Mastra 등 native trace 변환 | 특정 framework 사용 |
| OTel Collector | OTLP traces/logs/metrics 수집 | production observability 통합 |
| JSONL Import | structured local log 파일 import | custom/legacy/CI 환경 |
| API Webhook | run 완료 또는 finding 후보 발생 시 POST | SaaS/운영 연동 |
| Proxy/Gateway Log | LLM/tool/MCP gateway에서 request/response 수집 | closed-source agent |
| Observability Export | LangSmith/Langfuse/Phoenix/Logfire 등에서 export | 기존 observability 사용 |

### 주요 모듈

- `LangSmithAdapter`
- `OpenAIAgentsAdapter`
- `CrewAIAdapter`
- `AutoGenOtelAdapter`
- `LlamaIndexAdapter`
- `MastraAdapter`
- `GenericOtelGenAIAdapter`
- `MCPProxyAdapter`
- `JsonlAdapter`
- `WebhookReceiver`

## 4.3 Normalization Layer

각기 다른 trace/log 형식을 Judge Agent의 공통 schema로 변환한다.

### NormalizedAgentRun

```json
{
  "run_id": "string",
  "session_id": "string",
  "agent": {
    "id": "string",
    "name": "string",
    "version": "string",
    "framework": "string",
    "model": "string"
  },
  "input": {
    "user_request": "string",
    "messages": []
  },
  "instructions": {
    "system": "string",
    "developer": "string",
    "agent_role": "string",
    "tool_policy": "string",
    "memory_policy": "string",
    "safety_policy": "string"
  },
  "events": [],
  "final_output": "string",
  "metadata": {}
}
```

### 주요 처리

- span/event mapping
- parent-child 관계 복원
- timestamp ordering
- run/session correlation
- content redaction
- event deduplication
- missing field validation
- observability gap detection

## 4.4 Measurement Layer

정규화된 run에서 drift 탐지에 필요한 수치를 계산한다.

### Metric Categories

| Category | 주요 지표 |
|---|---|
| Prompt | instruction adherence, hierarchy compliance, format adherence |
| Tool | tool selection accuracy, argument correctness, sequence correctness |
| Context | context relevance, precision, recall, groundedness |
| Memory | retrieval precision/recall, update correctness, freshness, conflict resolution |
| Reasoning | plan quality, plan adherence, step efficiency, loop count |
| Goal | task completion, user goal alignment, scope expansion |
| Safety | approval compliance, guardrail violation, prompt injection resilience |
| Output | correctness, completeness, faithfulness, helpfulness |

### Metric Output

```json
{
  "run_id": "string",
  "metrics": {
    "instruction_adherence_score": 0.92,
    "tool_selection_accuracy": 0.80,
    "memory_retrieval_precision": 0.75,
    "verification_coverage": 0.40
  },
  "metric_evidence": {
    "verification_coverage": ["tool_call:e12", "final_response:e20"]
  }
}
```

## 4.5 Detection Layer

측정값과 trace를 기준으로 drift finding을 생성한다.

### 탐지 엔진

#### 4.5.1 Rule Checker Engine

결정적 규칙 기반 탐지.

예:

- approval 없이 external action 수행
- tool argument schema 위반
- memory 근거 없는 claim
- file edit 후 검증 없음
- 반복 tool loop

#### 4.5.2 LLM Judge Engine

rubric 기반 판단.

예:

- 응답이 사용자 목표를 충족하는가
- plan이 충분하고 효율적인가
- final response가 context에 faithful한가
- persona/tone이 일관적인가

#### 4.5.3 Baseline Comparator

현재 run을 baseline과 비교한다.

탐지 예:

- tool call 수 2배 증가
- category score 10점 이상 하락
- 새 High finding 발생
- verification coverage 하락

#### 4.5.4 Trace Analyzer

실행 경로 자체를 분석한다.

탐지 예:

- 비정상 loop
- 잘못된 handoff
- plan과 execution mismatch
- dependency 역순 실행

#### 4.5.5 Policy Checker

조직/제품별 policy를 검사한다.

탐지 예:

- 개인정보 출력 금지
- 결제/메일/게시 전 승인 필수
- destructive command 전 confirmation 필수

## 4.6 Analysis Layer

탐지된 finding을 정리하고, 원인과 개선 방향을 생성한다.

### 주요 모듈

- `FindingAggregator`
- `DuplicateMerger`
- `SeverityScorer`
- `ConfidenceCalibrator`
- `RootCauseAnalyzer`
- `ImpactAnalyzer`
- `RemediationGenerator`
- `RegressionFixtureGenerator`

### Finding Schema

```json
{
  "id": "JD-2026-001",
  "category": "tool",
  "metric": "argument_correctness_score",
  "severity": "high",
  "confidence": 0.87,
  "detection_method": "rule",
  "location": {
    "type": "tool_call",
    "ref": "span:e12"
  },
  "evidence": ["tool argument 'user_id' was generated without source context"],
  "expected": "Use user_id from authenticated session or ask for clarification",
  "actual": "Invented user_id=1234",
  "root_cause_hypothesis": "Tool schema lacks argument grounding rule",
  "impact": "Could operate on wrong user record",
  "recommendation": "Add argument grounding validation before tool execution",
  "regression_test_suggestion": "Fixture with missing user_id must block tool call"
}
```

## 4.7 Notification Layer

중요 drift가 발생했을 때 운영자나 CI/CD 시스템에 알린다.

### 알림 대상

- 개발자
- 운영자
- QA/evaluation 담당자
- 보안/정책 담당자
- CI/CD gate
- PR review thread
- incident channel

### 알림 채널

- Webhook
- Slack / Discord / Teams
- GitHub PR comment
- GitHub Check Run
- Email
- PagerDuty/Opsgenie
- Dashboard alert

### 알림 정책

| 조건 | 알림 수준 |
|---|---|
| Critical finding | 즉시 알림, release block |
| High finding 2개 이상 | 즉시 알림, review required |
| Safety/privacy finding | 즉시 알림 |
| Score threshold 하락 | 배치 요약 알림 |
| Low/Medium finding | daily/weekly report |
| Observability gap | warning |

### 알림 Payload

```json
{
  "run_id": "string",
  "agent_id": "string",
  "severity": "high",
  "title": "Tool argument drift detected",
  "summary": "Agent invented a tool argument not grounded in context",
  "evidence_refs": ["span:e12"],
  "report_url": "https://...",
  "recommended_action": "Block release and add grounding validation"
}
```

## 4.8 Reporting Layer

분석 결과를 사람이 읽고 실행 가능한 형태로 만든다.

### Report Types

| 리포트 | 용도 |
|---|---|
| Markdown Report | PR/문서/로컬 리뷰 |
| JSON Findings | 자동화/대시보드/API |
| CSV Summary | 운영 통계 |
| HTML Dashboard Export | 시각화 |
| CI Gate Result | release pass/block |
| Trend Report | 장기 drift 추세 |
| Incident Report | 장애/문제 대화 분석 |

### Markdown Report 구조

```markdown
# Judge Agent Drift Report

## Executive Summary
## Release Gate Recommendation
## Overall / Category Scores
## Critical and High Findings
## Findings by Category
## Evidence and Trace References
## Root Cause Analysis
## Recommended Remediation
## Regression Fixtures
## Observability Gaps
## Appendix
```

## 5. 시스템 간 연동 시나리오

## 5.1 CI/CD 연동

### 흐름

```text
Pull Request
  └─ Agent evaluation suite 실행
      └─ trace artifact 생성
          └─ Judge Agent analyze
              ├─ findings.json 생성
              ├─ report.md 생성
              └─ release gate 판정
                  ├─ pass
                  ├─ pass_with_warning
                  └─ block
```

### 연동 시스템

- GitHub Actions
- GitLab CI
- Jenkins
- Buildkite
- CircleCI

### 입력

- fixture dataset
- baseline findings
- current trace artifact
- rubric version

### 출력

- PR comment
- check status
- artifact upload
- release gate result

## 5.2 Production Monitoring 연동

### 흐름

```text
Production Agent
  └─ OTel traces / logs / metrics
      └─ Collector / Observability Backend
          └─ Judge Agent batch or streaming analyzer
              ├─ drift findings
              ├─ alerts
              └─ trend dashboard
```

### 운영 모드

- near-real-time alerting
- hourly batch analysis
- daily summary report
- incident-triggered deep analysis

### 주의사항

- production trace는 privacy redaction 필수
- 모든 run을 LLM judge로 평가하면 비용이 크므로 sampling 필요
- Critical signal은 rule checker로 빠르게 탐지

## 5.3 Observability Platform 연동

### 흐름

```text
LangSmith / Langfuse / Phoenix / Logfire / Datadog / SigNoz
  └─ trace export or API query
      └─ Judge Agent Adapter
          └─ NormalizedAgentRun
              └─ drift analysis
```

### 연동 방식

- trace id 기반 단건 분석
- project/run batch export
- webhook on run completion
- OTLP collector fan-out

### 장점

- 기존 trace 저장소 재사용
- production debugging과 evaluation 연결
- finding에서 원본 trace UI로 link 가능

## 5.4 Agent Runtime 직접 연동

### 흐름

```text
Agent Runtime
  └─ Judge SDK / Event Emitter
      └─ Judge Ingestion API
          └─ analysis queue
              └─ detector pipeline
```

### 사용 예

- 자체 agent framework
- 내부 업무 자동화 agent
- MCP tool-heavy agent

### 장점

- 의미 있는 custom metadata를 풍부하게 전달 가능
- memory/policy/approval 이벤트를 정확히 기록 가능

### 단점

- agent 코드 수정 필요
- SDK version 관리 필요

## 5.5 LLM / Tool Gateway 연동

### 흐름

```text
Agent
  ├─ LLM Gateway
  │   └─ prompt/response/usage log
  └─ Tool Gateway / MCP Proxy
      └─ tool call/result/error log
          └─ Judge Agent correlation by trace_id
```

### 사용 예

- closed-source agent
- 여러 agent가 동일 gateway 사용
- 중앙 정책/감사 환경

### 한계

- 내부 planning과 memory decision은 직접 보이지 않음
- agent intent/rationale은 별도 metadata 필요

## 6. 데이터 저장소 설계

## 6.1 저장 대상

| 저장소 | 내용 |
|---|---|
| Run Store | normalized run metadata |
| Event Store | normalized events / span tree |
| Metric Store | calculated metric values |
| Finding Store | drift findings |
| Report Store | markdown/html/json reports |
| Baseline Store | stable version metrics/findings |
| Fixture Store | regression fixtures |
| Rubric Store | metric rubric versions |
| Audit Store | access/export/alert history |

## 6.2 Retention 정책

| 데이터 | 권장 보관 |
|---|---|
| raw trace | 짧게, 예: 7~30일 |
| redacted normalized trace | 중간, 예: 30~90일 |
| findings | 길게, 예: 1년 이상 |
| aggregated metrics | 장기 보관 |
| reports | release/incident 기준 보관 |
| sensitive excerpts | 최소 보관 또는 저장 금지 |

## 7. 비동기 처리 아키텍처

긴 agent run이나 batch 분석을 고려해 비동기 pipeline을 사용한다.

```text
Ingestion API
  └─ Queue: normalize_jobs
      └─ Normalizer Worker
          └─ Queue: measurement_jobs
              └─ Metric Worker
                  └─ Queue: detection_jobs
                      └─ Detector Worker
                          └─ Queue: analysis_jobs
                              └─ Report/Alert Worker
```

### Queue Job Types

- `normalize_run`
- `calculate_metrics`
- `run_rule_checkers`
- `run_llm_judges`
- `compare_baseline`
- `aggregate_findings`
- `generate_report`
- `send_alerts`

## 8. API 설계 초안

## 8.1 Ingestion API

```http
POST /v1/runs
POST /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/complete
POST /v1/import/otel
POST /v1/import/jsonl
POST /v1/import/langsmith
```

## 8.2 Analysis API

```http
POST /v1/analyze
POST /v1/compare
POST /v1/fixtures
GET /v1/runs/{run_id}
GET /v1/runs/{run_id}/metrics
GET /v1/runs/{run_id}/findings
GET /v1/reports/{report_id}
```

## 8.3 Alert / Reporting API

```http
POST /v1/alerts/test
POST /v1/reports/generate
GET /v1/trends
GET /v1/baselines/{baseline_id}
POST /v1/baselines
```

## 9. 배포 형태

## 9.1 Local CLI

개발자 로컬 및 CI에서 사용.

```bash
judge-agent analyze --trace ./trace.json --output ./report.md
```

장점:

- 간단함
- privacy-friendly
- 빠른 도입

## 9.2 Server Mode

운영 환경에서 API/worker로 배포.

구성:

- ingestion API
- analysis workers
- storage DB
- report server
- alert dispatcher

## 9.3 Sidecar / Collector Mode

Agent runtime 옆에 배치해 trace를 수집한다.

장점:

- agent 코드 변경 최소화
- production observability와 자연스럽게 연동

## 9.4 SaaS / Central Evaluation Service

여러 agent/team/project의 drift를 중앙에서 관리한다.

필요 기능:

- multi-tenant isolation
- RBAC
- project-level rubric
- data retention policy
- audit log

## 10. 보안 모델

## 10.1 데이터 분류

| 등급 | 예 |
|---|---|
| Public | metric summary, aggregate trend |
| Internal | prompt templates, tool names, reports |
| Confidential | user messages, tool results, memory excerpts |
| Secret | API keys, credentials, tokens, private identifiers |

## 10.2 통제

- secret redaction
- PII detection
- role-based access control
- project-level data isolation
- audit logging
- external LLM judge opt-in
- report sharing permission

## 10.3 외부 LLM Judge 사용 정책

외부 judge 모델을 사용할 경우 다음을 명시한다.

- 어떤 trace 필드가 전송되는가
- redaction 적용 여부
- provider/model
- retention policy
- user/org approval status

## 11. 장애 및 실패 처리

| 실패 | 처리 |
|---|---|
| trace parse 실패 | partial run 생성, parse error finding |
| event 누락 | observability_gap finding |
| LLM judge timeout | retry 후 hypothesis로 degradation |
| report generation 실패 | JSON findings는 보존 |
| alert dispatch 실패 | retry queue, dead-letter queue |
| baseline 없음 | absolute score만 계산 |
| redaction 실패 | 외부 전송 차단 |

## 12. 운영 지표

Judge Agent 자체의 품질과 안정성을 측정한다.

### Pipeline Metrics

- ingestion success rate
- normalization error rate
- average analysis latency
- LLM judge cost per run
- report generation time
- alert delivery success rate

### Evaluation Quality Metrics

- finding precision
- finding recall
- false positive rate
- false negative rate
- judge consistency
- human override rate
- regression detection rate

### Coverage Metrics

- runs with tool trace
- runs with memory trace
- runs with context trace
- runs with instruction snapshot
- runs with safety events
- observability gap rate

## 13. 단계별 구현 로드맵

## Phase 1 — Local Batch MVP

목표: 파일 기반 agent trace를 분석해 report를 생성한다.

구현:

- NormalizedAgentRun schema
- JSONL/JSON trace import
- basic rule checkers
- LLM judge runner
- Markdown/JSON report

## Phase 2 — Framework Adapter

목표: 주요 framework trace를 직접 가져온다.

구현:

- Generic OTel GenAI adapter
- LangSmith adapter
- OpenAI Agents adapter
- LlamaIndex adapter
- Vercel AI SDK adapter

## Phase 3 — CI / Regression Gate

목표: PR/release 과정에서 drift regression을 차단한다.

구현:

- baseline store
- compare command
- GitHub Actions example
- PR comment/check output
- fixture generator

## Phase 4 — Server / Monitoring

목표: production trace를 지속적으로 분석한다.

구현:

- ingestion API
- async workers
- finding store
- alert dispatcher
- trend report

## Phase 5 — Enterprise Hardening

목표: 조직 단위 운영에 필요한 통제와 확장성을 제공한다.

구현:

- RBAC
- tenant/project isolation
- audit log
- retention policy
- external judge governance
- dashboard export

## 14. 권장 최소 구현 스택

초기 MVP 기준:

- Language: TypeScript 또는 Python
- CLI: Typer/Pydantic 또는 Node Commander/Zod
- Schema validation: Pydantic 또는 Zod
- Storage: local files → SQLite/Postgres 확장
- Queue: local async → Redis/Celery/BullMQ 확장
- Trace ingestion: JSONL + OTel JSON 우선
- Report: Markdown + JSON
- LLM Judge: provider-agnostic adapter

## 15. 핵심 인터페이스 초안

### Trace Adapter

```ts
interface TraceAdapter {
  name: string;
  canHandle(input: unknown): boolean;
  normalize(input: unknown): NormalizedAgentRun;
}
```

### Metric Calculator

```ts
interface MetricCalculator {
  metricName: string;
  category: DriftCategory;
  calculate(run: NormalizedAgentRun): MetricResult;
}
```

### Detector

```ts
interface Detector {
  id: string;
  category: DriftCategory;
  detect(run: NormalizedAgentRun, metrics: MetricResult[]): Finding[];
}
```

### Reporter

```ts
interface Reporter {
  format: "markdown" | "json" | "html";
  generate(report: DriftReport): string | Buffer;
}
```

### Alert Dispatcher

```ts
interface AlertDispatcher {
  channel: string;
  shouldSend(finding: Finding, policy: AlertPolicy): boolean;
  send(alert: AlertPayload): Promise<void>;
}
```

## 16. 결론

Judge Agent의 전체 아키텍처는 agent runtime과 직접 결합하지 않고, 수집/정규화/측정/탐지/분석/알림/리포팅을 분리한 pipeline 구조로 설계해야 한다.

핵심은 다음이다.

1. 다양한 agent/framework의 실행 데이터를 adapter로 수집한다.
2. 모든 입력을 `NormalizedAgentRun`으로 표준화한다.
3. deterministic rule과 LLM judge를 결합해 drift를 탐지한다.
4. finding은 evidence와 remediation을 반드시 포함한다.
5. CI, observability platform, production monitoring, alerting 시스템과 연동한다.
6. privacy와 redaction을 기본 설계로 둔다.
7. trace 누락 자체도 운영 리스크로 탐지한다.

이 구조를 따르면 Judge Agent는 단순한 평가 스크립트가 아니라, agent 품질과 drift를 지속적으로 관리하는 독립적인 evaluation/observability 시스템으로 확장될 수 있다.
