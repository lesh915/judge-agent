# Judge Agent 활용 시나리오: AI Agent DevOps / CI-CD 검증 프로세스

## 1. 개요

Judge Agent는 AI agent 개발에서 DevOps의 CI/CD 테스트·검증 프로세스와 유사한 역할을 수행할 수 있다.

전통적인 소프트웨어 개발에서는 코드 변경이 발생하면 다음 검증을 거친다.

```text
code change
  -> unit test
  -> integration test
  -> lint/typecheck
  -> security scan
  -> build
  -> deploy gate
```

AI agent 개발에서는 코드뿐 아니라 다음 요소가 agent 동작을 바꾼다.

- prompt 변경
- system/developer instruction 변경
- tool schema 변경
- tool implementation 변경
- memory policy 변경
- retrieval context 변경
- LangGraph workflow 변경
- model/provider 변경
- guardrail/approval policy 변경

따라서 AI agent에도 별도의 검증 pipeline이 필요하다.

Judge Agent는 이 과정에서 **Agent Behavior CI/CD Gate** 역할을 한다.

```text
agent change
  -> reference scenario 실행
  -> trace 수집
  -> drift metric 측정
  -> regression 탐지
  -> report 생성
  -> release pass/warning/block 결정
```

## 2. Judge Agent의 DevOps적 역할

## 2.1 Unit Test에 해당하는 역할

개별 기능 단위의 agent behavior를 검증한다.

예:

- 특정 user input에서 반드시 `read_log_file` tool을 호출해야 한다.
- `filter_log_records`에는 사용자가 요청한 endpoint가 argument로 들어가야 한다.
- output format은 정해진 markdown section을 포함해야 한다.

Judge Agent 관점:

- tool selection correctness
- argument correctness
- output contract compliance
- required node execution

## 2.2 Integration Test에 해당하는 역할

LLM, tools, retriever, memory, LangGraph workflow가 함께 동작할 때 문제가 없는지 검증한다.

예:

```text
parse_request
  -> load_logs
  -> parse_logs
  -> filter_logs
  -> compute_metrics
  -> detect_anomalies
  -> validate_findings
  -> generate_report
```

Judge Agent 관점:

- graph node sequence correctness
- tool result grounding
- state transition validity
- context groundedness

## 2.3 Regression Test에 해당하는 역할

prompt, model, tool, graph 변경 후 기존에 잘 되던 시나리오가 깨졌는지 확인한다.

예:

- prompt 수정 후 tool 호출이 줄어들거나 불필요하게 증가함
- model 변경 후 JSON output schema 위반 증가
- retriever 설정 변경 후 context grounding score 하락
- graph edge 조건 수정 후 validation node가 skip됨

Judge Agent 관점:

- baseline vs current score 비교
- 새 High/Critical finding 탐지
- category별 metric delta 추적

## 2.4 Lint / Static Analysis에 해당하는 역할

agent 실행 전후의 구조적 문제를 점검한다.

예:

- tool schema에 required field 설명이 부족함
- prompt에 output contract가 없음
- LangGraph에 error branch가 없음
- approval이 필요한 node 앞에 approval guard가 없음

Judge Agent 관점:

- observability gap
- missing instruction snapshot
- missing tool policy
- missing validation node

## 2.5 Security Scan에 해당하는 역할

agent가 안전·권한·개인정보 정책을 위반하지 않는지 확인한다.

예:

- 외부 action 전 승인 누락
- sensitive value가 report에 노출됨
- prompt injection성 context를 instruction처럼 따름
- destructive tool을 validation 없이 실행함

Judge Agent 관점:

- safety violation count
- permission compliance
- sensitive data exposure
- prompt injection resilience

## 2.6 Release Gate에 해당하는 역할

분석 결과를 바탕으로 배포 가능 여부를 결정한다.

예:

```text
score >= 85 and no High/Critical -> pass
score >= 70 and no Critical      -> warning
score < 70 or Critical exists    -> block
```

## 3. 활용 시나리오

## 3.1 Pull Request 검증 시나리오

### 상황

개발자가 LangGraph 기반 웹로그 분석 에이전트의 prompt를 수정했다.

### 흐름

```text
1. Pull Request 생성
2. GitHub Actions에서 reference fixture 실행
3. LangSmith 또는 JSONL trace 저장
4. Judge Agent가 trace 분석
5. findings.json / report.md 생성
6. PR comment로 결과 게시
7. release gate 결정
```

### Judge Agent가 보는 것

- prompt 변경 후 tool 호출이 유지되는가
- required node가 모두 실행되는가
- final report가 evidence 기반인가
- baseline 대비 metric이 하락했는가

### 결과 예

```text
Release Gate: block
Reason:
- High: validation node skipped
- Medium: final report missing Evidence section
```

## 3.2 Prompt 변경 Regression 검증

### 상황

웹로그 분석 agent의 system prompt를 더 짧게 바꿨다.

### 위험

- tool 사용 지침이 약해짐
- evidence section 누락
- 불확실성 표현이 줄어듦

### Judge Agent 검증

- instruction adherence score
- output format compliance
- evidence coverage
- hallucinated completion claim

### 기대 효과

prompt 변경이 기능 regression을 만들었는지 자동 확인할 수 있다.

## 3.3 Tool Schema 변경 검증

### 상황

`filter_log_records` tool의 argument 이름이 `path_pattern`에서 `endpoint_pattern`으로 변경되었다.

### 위험

- agent가 이전 argument를 계속 사용
- tool call이 실패
- 실패를 무시하고 final report 생성

### Judge Agent 검증

- tool argument schema mismatch
- tool error handling
- final answer consistency

### 기대 결과

```json
{
  "category": "tool",
  "metric": "tool_argument_correctness",
  "severity": "high",
  "recommendation": "Update prompt/tool description to use endpoint_pattern"
}
```

## 3.4 LangGraph Workflow 변경 검증

### 상황

개발자가 workflow를 단순화하면서 `validate_findings` node를 제거했다.

### 위험

- 근거 없는 분석 결과가 report에 포함됨
- tool result와 final answer 불일치 증가

### Judge Agent 검증

- node sequence correctness
- required node missing
- graph completion path validity
- report evidence consistency

### Release Gate

validation node가 required policy에 포함되어 있다면 `block`.

## 3.5 Model 변경 검증

### 상황

비용 절감을 위해 model을 `gpt-4.1`에서 더 작은 모델로 변경했다.

### 위험

- tool selection 정확도 하락
- output format 위반 증가
- context grounding 하락
- overconfidence 증가

### Judge Agent 검증

- baseline/current metric delta
- tool selection accuracy
- answer context groundedness
- output format compliance
- score trend

### 기대 효과

모델 변경이 비용은 줄였지만 품질 regression을 만들었는지 확인한다.

## 3.6 Retriever / RAG 설정 변경 검증

### 상황

runbook retriever의 top_k를 5에서 2로 줄였다.

### 위험

- 필요한 context 누락
- final answer가 source 없이 생성됨
- 잘못된 runbook을 근거로 사용

### Judge Agent 검증

- retrieval context relevance
- retrieval context precision
- missing required context
- answer context groundedness

## 3.7 Memory / State 정책 변경 검증

### 상황

LangGraph checkpoint 저장 방식 또는 memory policy를 변경했다.

### 위험

- stale state 사용
- 이전 run의 target endpoint가 현재 run에 섞임
- state update 누락

### Judge Agent 검증

- state freshness score
- state value grounding
- unsupported memory claim
- graph state transition validity

## 3.8 Production Incident 사후 분석

### 상황

운영 중 웹로그 분석 agent가 잘못된 장애 원인을 보고했다.

### 흐름

```text
1. incident run_id 확보
2. LangSmith trace export
3. Judge Agent deep analysis 실행
4. drift finding과 root cause 확인
5. regression fixture 생성
6. 다음 PR부터 동일 문제 방지
```

### Judge Agent가 찾는 것

- 잘못된 endpoint filter
- parse error 무시
- retrieved runbook과 final report 충돌
- validation node skip
- baseline 대비 tool loop 증가

## 3.9 Nightly Agent Evaluation

### 상황

매일 밤 reference fixture 전체를 실행해 agent 품질 추세를 확인한다.

### 흐름

```text
nightly schedule
  -> fixture dataset 실행
  -> trace 수집
  -> Judge Agent batch analyze
  -> trend report 생성
  -> score 하락 시 알림
```

### 측정 항목

- category score trend
- High/Critical finding count
- tool error rate
- context groundedness
- output format compliance
- average analysis latency/cost

## 3.10 Release Candidate 검증

### 상황

새 agent version을 production에 배포하기 전 최종 검증한다.

### 검증 세트

- happy path
- edge case
- malformed log
- insufficient data
- high error rate
- latency spike
- suspicious IP
- parse error
- missing baseline

### Gate

- Critical finding 있으면 release block
- High finding 2개 이상이면 release block
- score 70 미만이면 release block
- observability gap이 심하면 manual review required

## 4. CI/CD Pipeline 예시

## 4.1 GitHub Actions 흐름

```yaml
name: Agent Evaluation

on:
  pull_request:
    paths:
      - "agents/**"
      - "prompts/**"
      - "tools/**"
      - "graphs/**"
      - "fixtures/**"

jobs:
  judge-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run reference agent fixtures
        run: |
          python reference-agents/weblog-analysis-agent/run_fixtures.py \
            --output traces/current

      - name: Analyze traces with Judge Agent
        run: |
          judge-agent-simple analyze-batch \
            --traces traces/current \
            --baseline baselines/main.json \
            --output reports/judge-report.md \
            --json reports/findings.json \
            --fail-on high

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: judge-agent-report
          path: reports/
```

## 4.2 Exit Code 정책

| 결과 | Exit Code | 의미 |
|---|---:|---|
| pass | 0 | 배포 가능 |
| warning | 0 | 배포 가능하지만 리뷰 권장 |
| block | 1 | 배포 차단 |
| analyzer_error | 2 | Judge Agent 실행 오류 |
| observability_error | 3 | trace 부족으로 평가 불가 |

## 5. PR Comment 예시

```markdown
## Judge Agent Report

Release Gate: BLOCK
Overall Score: 68

### High Findings

1. Tool Argument Drift
   - `filter_log_records.path_pattern` expected `/api/login`, got `/api/payment`
   - Recommendation: ensure parse_request targetPath is passed to filter_logs node

2. Missing Validation Node
   - `validate_findings` was skipped before `generate_report`
   - Recommendation: restore validation edge before report generation

### Artifacts

- Full report: reports/judge-report.md
- Findings JSON: reports/findings.json
```

## 6. DevOps 관점의 Artifact

Judge Agent는 다음 artifact를 생성한다.

| Artifact | 역할 |
|---|---|
| `findings.json` | 자동화 시스템이 읽는 구조화 결과 |
| `report.md` | 개발자 리뷰용 리포트 |
| `metrics.json` | score trend와 dashboard용 데이터 |
| `fixtures/*.yaml` | 재발 방지 regression fixture |
| `baseline.json` | main/release 기준 품질 상태 |
| `trace-summary.json` | 원본 trace 요약 |

## 7. Baseline 관리

Baseline은 stable branch 또는 release version의 Judge Agent 결과다.

```text
main branch baseline
  -> PR current result와 비교
release baseline
  -> next release candidate와 비교
production baseline
  -> production monitoring trend와 비교
```

Baseline에 포함할 것:

- overall score
- category scores
- known accepted findings
- fixture별 expected result
- prompt/tool/graph/model version

## 8. Human Review가 필요한 경우

모든 drift를 자동으로 block하면 false positive가 문제가 될 수 있다.

수동 리뷰가 필요한 경우:

- LLM judge confidence < 0.7
- 새 metric이 calibration 중
- trace가 일부 누락됨
- business rule이 변경됨
- finding은 있으나 expected behavior가 불명확함

Judge Agent는 이런 경우 `manual_review_required`를 반환한다.

## 9. Judge Agent를 적용하기 좋은 시점

우선 도입하기 좋은 상황:

- prompt를 자주 수정하는 agent
- tool call이 많은 agent
- LangGraph workflow가 있는 agent
- 운영 리포트/분석 결과를 생성하는 agent
- 잘못된 결과가 고객/운영 의사결정에 영향을 주는 agent
- 모델 교체나 비용 최적화를 계획 중인 agent

웹로그 분석 agent는 위 조건을 잘 만족하므로 첫 reference target으로 적합하다.

## 10. 기대 효과

Judge Agent를 CI/CD에 포함하면 다음 효과를 기대할 수 있다.

- prompt 변경으로 인한 regression 조기 발견
- tool schema 변경 영향 자동 확인
- LangGraph workflow drift 탐지
- 모델 변경 전후 품질 비교
- 운영 incident를 regression fixture로 전환
- agent release gate 자동화
- agent 품질 추세 관리

## 11. 결론

Judge Agent는 AI agent 개발에서 테스트, 검증, 회귀 탐지, release gate 역할을 수행할 수 있다.

전통 DevOps가 코드 품질을 자동 검증하듯, Judge Agent는 agent의 행동 품질을 자동 검증한다.

특히 LangChain/LangGraph 기반 agent에서는 trace를 통해 다음을 검증할 수 있다.

- 올바른 node 순서
- 올바른 tool 사용
- argument와 state의 정합성
- retrieved context 기반 응답
- 검증 완료 후 final report 생성
- baseline 대비 품질 regression

따라서 simple 버전 Judge Agent는 먼저 웹로그 분석 agent fixture를 기준으로 CI/CD 검증 프로세스를 구현하고, 이후 다양한 agent 도메인으로 확장하는 것이 좋다.
