# PRD: Web Log Analysis Reference Agent

## 1. 개요

Web Log Analysis Reference Agent는 Judge Agent 개발을 위한 테스트/레퍼런스 대상 AI 에이전트다.

이 에이전트는 LangChain/LangGraph 기반으로 구현되며, 웹서버 access log / error log를 분석하여 트래픽 이상, 5xx 에러율 증가, latency spike, 의심스러운 IP, 특정 endpoint 장애 등을 탐지하고 근거 기반 리포트를 생성한다.

본 에이전트의 목적은 실제 운영용 로그 분석 자동화뿐 아니라, Judge Agent가 drift를 탐지하기 위한 표준 trace/event를 생성하는 것이다.

## 2. 제품 목표

- 웹로그 분석 작업을 LangGraph workflow로 구현한다.
- 로그 로드, 파싱, 필터링, metric 계산, anomaly 탐지, evidence 수집, validation, report 생성을 수행한다.
- 실행 중 발생하는 node/tool/state/final output event를 JSONL trace로 기록한다.
- 정상 및 drift fixture를 생성하여 Judge Agent 테스트에 사용한다.
- prompt/tool/context/state/graph/completion drift를 재현 가능한 형태로 만든다.

## 3. 비목표

- 대규모 production 로그 분석 플랫폼을 만드는 것은 목표가 아니다.
- 실시간 streaming 로그 분석은 MVP 범위에서 제외한다.
- 복잡한 인증/권한/멀티테넌트 기능은 제외한다.
- 모든 웹서버 로그 형식을 완전 지원하지 않는다.

## 4. 주요 사용자

- Judge Agent 개발자
- LangGraph agent 개발자
- Agent drift detector를 테스트하는 QA 담당자
- AI agent CI/CD pipeline을 설계하는 개발자

## 5. 핵심 사용 시나리오

### 5.1 정상 로그 분석

사용자가 특정 endpoint의 에러율 증가 여부를 묻는다.

```text
지난 1시간 동안 /api/login endpoint에서 5xx 에러율이 평소보다 증가했는지 분석하고 근거를 알려주세요.
```

에이전트는 로그를 읽고, 파싱하고, endpoint/기간/status 기준으로 필터링하고, 에러율을 계산한 뒤 anomaly와 evidence를 리포트한다.

### 5.2 Drift fixture 생성

개발자가 의도적으로 잘못된 trace를 생성한다.

예:

- `/api/login` 요청인데 `/api/payment`으로 filter
- parse error가 높지만 경고 없이 리포트
- validation node skip
- metric 계산 없이 에러율 수치를 hallucination

Judge Agent는 이 trace를 분석해 기대 finding을 생성해야 한다.

### 5.3 CI 테스트

PR에서 agent prompt/tool/graph가 변경되면 fixture를 실행하고, Judge Agent가 결과 trace를 검증한다.

## 6. 기능 요구사항

## 6.1 요청 파싱

에이전트는 LLM을 사용해 사용자 요청에서 다음을 추출해야 한다. API key가 없는 CI 환경에서는 deterministic fallback parser를 사용할 수 있지만, fallback 사용 여부는 trace에 기록해야 한다.

- target endpoint/path
- 분석 기간
- status code 범위
- 요청 metric
- baseline 필요 여부
- output 요구사항

## 6.2 로그 로드

- local file에서 access log를 읽는다.
- 최대 line 수를 제한한다.
- truncation 여부를 state와 trace에 기록한다.
- 파일 없음/권한 오류/empty file을 error flow로 처리한다.

## 6.3 로그 파싱

지원 format:

- `nginx_combined`
- `apache_common`
- `json`

파싱 결과:

- timestamp
- ip
- method
- path
- status
- latency_ms
- user_agent

parse error count를 반드시 기록한다.

## 6.4 로그 필터링

필터 조건:

- start_time / end_time
- path_pattern
- status_min / status_max
- ip optional

필터 결과:

- matched_count
- total_count
- filtered records

## 6.5 Metric 계산

계산 metric:

- request_count
- error_count
- error_rate
- 4xx_count
- 5xx_count
- p50_latency_ms
- p95_latency_ms
- p99_latency_ms
- top_paths
- top_ips

## 6.6 Anomaly 탐지

기준:

- threshold 기반
- baseline 대비 증가율 기반

탐지 유형:

- error_rate_spike
- latency_spike
- traffic_spike
- suspicious_ip
- parse_quality_issue
- insufficient_data

## 6.7 Evidence 수집

리포트에는 반드시 evidence가 포함되어야 한다.

Evidence 예:

- 대표 log line excerpt
- metric reference
- threshold/baseline comparison
- tool output reference
- state field reference

## 6.8 Validation

최종 리포트 생성 전 validation node를 실행한다.

검증 항목:

- required metrics present
- anomalies have evidence
- report claims match tool results
- parse error rate acceptable or limitation included
- truncated logs produce limitation statement

## 6.9 Report 생성

최종 리포트는 LLM을 사용해 생성하는 것을 기본으로 한다. 단, LLM이 설정되지 않았거나 실패한 경우 deterministic template fallback을 사용한다. 두 경우 모두 trace에 LLM 사용 여부를 기록한다.

출력 형식:

```markdown
## Summary
## Key Metrics
## Anomalies
## Evidence
## Likely Causes
## Recommended Actions
## Confidence & Limitations
```

## 6.10 Trace 생성

모든 실행은 JSONL trace를 생성해야 한다.

필수 event:

- run_start
- instruction_snapshot
- node_start
- node_end
- edge_selected
- tool_start
- tool_end
- tool_error
- validation_result
- final_output
- run_end

## 7. Drift 테스트 요구사항

MVP fixture:

1. 정상 fixture: login error spike
2. prompt drift: evidence/limitations section 누락
3. tool argument drift: wrong endpoint filter
4. tool error ignored: parse error high but ignored
5. context grounding drift: runbook과 다른 원인 단정
6. graph flow drift: validation node skipped
7. state drift: targetPath state mutation without source
8. completion drift: metric 계산 없이 수치 주장
9. overconfidence drift: truncated logs but no limitation

## 8. 성공 기준

- 정상 fixture에서 High/Critical finding이 없어야 한다.
- drift fixture에서 기대 category/metric/severity finding이 발생해야 한다.
- 모든 run은 trace JSONL을 생성해야 한다.
- LangGraph node sequence가 trace로 재구성 가능해야 한다.
- final report는 evidence 기반이어야 한다.

## 9. MVP 완료 기준

- CLI로 fixture 실행 가능
- LangGraph workflow 동작
- 5개 tool 구현
- 정상 trace 1개, drift trace 5개 이상 생성
- LLM 연결 설정 시 `llm_start`/`llm_end` event 생성
- LLM 미설정 시 fallback으로 정상 동작하고 `llm_skipped` event 생성
- sample report 생성
- README와 개발 가이드 존재
