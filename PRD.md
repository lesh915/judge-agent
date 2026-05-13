# PRD: Judge Agent — Agent Drift 탐지/분석/가이드 시스템

## 1. 개요

Judge Agent는 AI agent의 동작이 의도된 역할, 정책, 품질 기준, 사용자 기대에서 벗어나는 **agent drift**를 탐지하고, 원인을 분석하며, 개선 가이드를 제공하는 평가/감시용 agent다.

본 제품의 핵심 개발 사항은 기존 **LLM-as-a-Judge**의 탐지/분석 지표를 확장하여, 일반 LLM 응답 품질뿐 아니라 Agent 구조상 발생하는 drift를 체계적으로 탐지하는 기준과 지표를 정의하고 이를 기반으로 자동 분석을 수행하는 것이다.

Judge Agent는 다음 요소를 모두 평가 대상으로 삼는다.

- LLM response quality
- Prompt / instruction adherence
- Tool selection, argument mapping, sequencing
- Context / memory retrieval, storage, update, conflict handling
- Execution trajectory and step efficiency
- Safety, permission, environment guardrails
- Final task completion and user-goal alignment

## 2. 배경 및 웹 리서치 요약

### 2.1 기존 LLM-as-a-Judge 평가 방식

LLM-as-a-Judge는 모델 출력물을 사람이 정의한 rubric 또는 reference answer와 비교해 평가한다. 일반적인 평가 방식은 다음과 같다.

- **Single-output, reference-free 평가**: 정답 없이 rubric만으로 하나의 응답을 평가
- **Single-output, reference-based 평가**: gold/reference answer와 비교해 평가
- **Pairwise 평가**: 두 응답 중 더 나은 결과를 선택
- **G-Eval 방식**: 평가 기준과 단계적 reasoning을 통해 coherence, fluency, consistency, relevance 등 자연어 생성 품질을 평가
- **Structured output judge**: JSON schema 등 구조화된 verdict를 강제해 평가 결과의 파싱 가능성과 일관성을 높임

기존 LLM 평가의 대표 지표는 다음과 같다.

- Answer relevancy
- Helpfulness
- Correctness
- Faithfulness / groundedness
- Completeness
- Coherence
- Fluency
- Bias / toxicity
- Format adherence
- Safety / policy compliance

### 2.2 Agent 평가가 LLM 평가와 다른 점

Agent는 단일 prompt-response 시스템이 아니라, LLM이 계획을 세우고, 도구를 선택하고, 환경과 상호작용하며, memory/context를 사용해 여러 step을 수행하는 시스템이다. 따라서 최종 응답만 평가하면 drift를 놓친다.

웹 리서치에서 공통적으로 강조된 Agent 평가 축은 다음과 같다.

- Agent 평가는 **final output**뿐 아니라 **execution trajectory**를 평가해야 한다.
- 도구 사용 agent는 **tool name, arguments, output interpretation, sequence**를 별도로 평가해야 한다.
- memory가 있는 agent는 **memory write/read/update/retrieval conflict**를 평가해야 한다.
- multi-step agent는 **plan quality, plan adherence, step efficiency, loop/redundancy**를 평가해야 한다.
- production agent는 **safety guardrail, permission, environment constraints**를 평가해야 한다.
- deterministic check와 LLM judge를 혼합해야 한다.

### 2.3 참고 자료

- Braintrust, “AI agent evaluation: A practical framework for testing multi-step agents” — reasoning/action/end-to-end/safety layer별 평가, tool correctness, argument correctness, path validity, regression gates 강조
- arXiv, “Beyond Task Completion: An Assessment Framework for Evaluating Agentic AI Systems” — LLM/Memory/Tools/Environment 네 pillar와 instruction adherence, memory retrieval, tool sequencing, error interpretation 등 제시
- Confident AI, “LLM-as-a-Judge Simply Explained” — single-output, reference-based/reference-free, pairwise judge, rubric 기반 scoring 방식 정리
- Comet, “Structured Generation for LLM-as-a-Judge Evaluations” — judge 결과를 구조화해 신뢰성과 자동화 가능성을 높이는 방식 설명
- G-Eval 관련 자료 — coherence, fluency, consistency, relevance 등 reference-free generation evaluation 방식
- RAG evaluation 자료 — faithfulness, answer relevancy, contextual precision/recall 등 context-grounding 지표

## 3. 문제 정의

AI agent는 시간이 지나며 다음과 같은 drift를 보일 수 있다.

- 역할 drift: 원래 맡은 역할과 다른 방식으로 행동함
- 정책 drift: 시스템/개발자/조직 정책을 점진적으로 무시함
- prompt drift: 상위 instruction, persona, output contract에서 벗어남
- tool drift: 필요한 도구를 쓰지 않거나, 잘못된 도구/인자/순서로 실행함
- context drift: 현재 작업과 무관하거나 오래된 context를 사용함
- memory drift: memory를 잘못 검색/저장/갱신하거나, 충돌 정보를 해결하지 못함
- reasoning drift: 계획이 부실하거나 계획과 실행이 어긋남
- safety drift: 승인/권한/가드레일을 무시함
- 품질 drift: 정확성, 근거 제시, 검증 수준이 낮아짐
- 목표 drift: 사용자의 요청보다 agent 자신의 추정 목표를 우선시함

현재 많은 agent 운영 환경에서는 drift를 사후에 사람이 수동으로 발견한다. 이는 느리고, 재현성이 낮으며, 운영 규모가 커질수록 관리가 어렵다.

## 4. 제품 목표

### 4.1 핵심 목표

- Agent drift 탐지 기준/지표를 정의한다.
- Prompt, tools, context, memory, execution trajectory별 drift를 자동 탐지한다.
- 기존 LLM-as-a-Judge 평가 지표를 Agent 평가 지표로 확장한다.
- Deterministic checker와 LLM judge를 결합한다.
- 각 drift finding에 근거, 심각도, 신뢰도, 원인, 개선 가이드를 제공한다.
- Baseline 대비 drift 변화와 regression을 추적한다.

### 4.2 비목표

- 운영 agent를 사용자 승인 없이 자동 수정하지 않는다.
- 모든 drift를 100% 자동 확정하지 않는다.
- 단순 quality score만 제공하는 평가 도구에 머무르지 않는다.
- 외부 시스템에 리포트나 패치를 무단 전송하지 않는다.

## 5. 주요 사용자

- Agent 개발자
- AI 운영 담당자
- QA / Evaluation 담당자
- 보안/정책 담당자
- Prompt engineer
- Tool/API integration engineer

## 6. 핵심 개념

### 6.1 Agent Drift

Agent가 명시적 지침, 기대 행동, 기준 응답 패턴, 도구 사용 정책, memory 사실관계, safety policy 또는 task objective에서 벗어나는 현상.

### 6.2 Drift Event

하나의 대화 턴, tool call, memory operation, planning step, file change, final response에서 발견된 drift 후보.

### 6.3 Drift Finding

Judge Agent가 deterministic rule, baseline comparison, LLM judge 중 하나 이상의 방법으로 근거를 확보한 drift 항목.

### 6.4 Drift Metric

Drift를 수치화하기 위한 기준. 예: instruction adherence score, tool selection accuracy, memory retrieval precision, plan adherence score.

### 6.5 Guidance

Drift를 줄이기 위한 구체적 개선안. 예: prompt 수정, tool schema 보강, memory policy 개선, regression fixture 추가.

## 7. 평가 프레임워크

Judge Agent는 다음 6개 layer로 agent를 평가한다.

### 7.1 LLM Output Layer

기존 LLM-as-a-Judge 방식으로 최종 응답 품질을 평가한다.

주요 지표:

- Answer relevance
- Correctness
- Faithfulness / groundedness
- Completeness
- Helpfulness
- Coherence
- Conciseness
- Format adherence
- Safety compliance

### 7.2 Prompt / Instruction Layer

Agent가 system/developer/user instruction, persona, output contract, channel rule을 지키는지 평가한다.

주요 지표:

- Instruction adherence score
- Hierarchy compliance score
- Output contract compliance
- Persona consistency score
- Refusal correctness
- Clarification appropriateness

### 7.3 Planning / Reasoning Layer

Agent가 적절한 계획을 세우고 실행 중 계획을 따르는지 평가한다.

주요 지표:

- Plan quality
- Plan completeness
- Plan adherence
- Reasoning consistency
- Step necessity ratio
- Loop/redundancy count
- Recovery quality

### 7.4 Tool / Action Layer

Agent가 필요한 도구를 정확히 선택하고 올바른 인자와 순서로 실행하는지 평가한다.

주요 지표:

- Tool selection accuracy
- Tool necessity score
- Argument correctness
- Schema compliance
- Tool sequencing correctness
- Output interpretation correctness
- Error handling correctness
- Authorization adherence

### 7.5 Context / Memory Layer

Agent가 memory/context를 정확히 검색, 사용, 저장, 갱신하는지 평가한다.

주요 지표:

- Context relevance
- Context precision
- Context recall
- Memory retrieval accuracy
- Memory update correctness
- Memory freshness
- Memory conflict resolution
- Unsupported memory claim rate
- Privacy leakage count

### 7.6 Environment / Safety Layer

Agent가 운영 환경, 권한, 정책, 외부 action 제한을 지키는지 평가한다.

주요 지표:

- Guardrail violation count
- Permission check rate
- External action approval compliance
- Destructive action safety compliance
- Prompt injection resilience
- Sensitive data exposure count
- Environment constraint adherence

## 8. Drift Taxonomy 및 탐지 기준

### 8.1 Prompt Drift

Agent가 prompt hierarchy, role, persona, output format, interaction style에서 벗어나는 현상.

탐지 기준:

- 상위 지침과 충돌하는 응답 생성
- 사용자 요구 형식 미준수
- 지정 persona/tone 위반
- instruction priority 오해
- 과도한 autonomy 또는 임의 목표 설정

대표 지표:

- `instruction_adherence_score`
- `hierarchy_violation_count`
- `format_violation_count`
- `persona_consistency_score`

### 8.2 Tool Drift

Agent가 tool을 사용해야 할 때 사용하지 않거나, 잘못된 도구/인자/순서로 사용하는 현상.

탐지 기준:

- tool 필요 상황에서 tool 미사용
- 잘못된 tool 선택
- required parameter 누락
- context에 없는 값을 argument로 생성
- tool 결과와 다른 결론 도출
- tool call loop 또는 중복 호출
- 외부/파괴적 action 전에 승인 생략

대표 지표:

- `tool_selection_accuracy`
- `tool_call_necessity_score`
- `argument_correctness_score`
- `tool_sequence_correctness`
- `tool_output_grounding_score`
- `redundant_tool_call_count`
- `approval_compliance_rate`

### 8.3 Context Drift

Agent가 현재 task와 무관한 context를 사용하거나 필요한 context를 누락하는 현상.

탐지 기준:

- 질문과 관련 없는 context 사용
- 필요한 context retrieval 누락
- 오래된 context를 최신 사실처럼 사용
- context와 충돌하는 답변 생성
- trace에 존재하지 않는 근거를 주장

대표 지표:

- `context_relevance_score`
- `context_precision`
- `context_recall`
- `context_groundedness_score`
- `stale_context_usage_count`

### 8.4 Memory Drift

Agent가 장기/단기 memory를 잘못 검색, 저장, 갱신, 해석하는 현상.

탐지 기준:

- memory에 없는 사실을 기억한다고 주장
- 충돌 memory를 해결하지 않고 사용
- 사용자 선호를 잘못 적용
- 업데이트해야 할 memory를 누락
- 저장하면 안 되는 민감정보 저장
- memory freshness 확인 없이 오래된 정보를 사용

대표 지표:

- `memory_retrieval_precision`
- `memory_retrieval_recall`
- `memory_update_correctness_rate`
- `memory_conflict_resolution_score`
- `unsupported_memory_claim_rate`
- `memory_privacy_violation_count`

### 8.5 Reasoning / Trajectory Drift

Agent의 계획, 실행 경로, 검증 단계가 task 목적에서 벗어나는 현상.

탐지 기준:

- 계획이 task를 충분히 커버하지 못함
- 계획과 실행 불일치
- 불필요한 step 증가
- 같은 행동 반복
- 실패 후 회복 전략 부재
- 검증 없이 완료 선언

대표 지표:

- `plan_quality_score`
- `plan_adherence_score`
- `step_efficiency`
- `loop_count`
- `verification_coverage`
- `recovery_success_rate`

### 8.6 Goal Drift

Agent가 사용자의 명시적 목표보다 자체 추정 목표, 부가 작업, 장기 목표를 우선하는 현상.

탐지 기준:

- 요청하지 않은 범위 확장
- 핵심 요청 미완료 상태에서 부가 작업 수행
- 사용자 의도를 과도하게 해석
- 완료 기준 불일치

대표 지표:

- `user_goal_alignment_score`
- `scope_expansion_count`
- `task_completion_score`
- `unrequested_action_count`

### 8.7 Safety / Permission Drift

Agent가 승인, 권한, privacy, destructive action, external action 정책을 위반하는 현상.

탐지 기준:

- 외부 메시지/이메일/게시물 무단 전송
- destructive command 전 승인 누락
- 민감정보 노출
- prompt injection에 따른 instruction override
- 권한 확대 또는 safeguard 우회 유도

대표 지표:

- `safety_violation_count`
- `permission_check_rate`
- `external_action_approval_rate`
- `destructive_action_compliance`
- `prompt_injection_resilience_score`
- `sensitive_data_exposure_count`

## 9. 탐지 방법론

Judge Agent는 단일 LLM judge에만 의존하지 않고 다음 방법을 조합한다.

### 9.1 Deterministic Rule Check

정확히 판정 가능한 항목에 사용한다.

예:

- JSON schema validity
- required field presence
- tool name correctness
- argument type correctness
- forbidden command pattern
- external action approval presence
- output format compliance
- duplicate/loop tool call detection

### 9.2 Reference-based Judge

정답 또는 expected trajectory가 있는 경우 사용한다.

예:

- expected tool sequence와 실제 sequence 비교
- expected answer와 final answer 비교
- expected memory update와 실제 update 비교

### 9.3 Reference-free LLM Judge

정답이 없지만 rubric으로 평가 가능한 경우 사용한다.

예:

- helpfulness
- coherence
- plan quality
- reasoning consistency
- persona consistency
- recovery quality

### 9.4 Pairwise / Baseline Comparison

이전 안정 버전 또는 다른 prompt/model과 비교한다.

예:

- current run이 baseline 대비 tool call 수가 증가했는가
- instruction adherence가 하락했는가
- memory hallucination이 새로 생겼는가

### 9.5 Trace-based Analysis

Agent의 전체 trajectory를 분석한다.

필수 trace 요소:

- user input
- selected instructions
- retrieved context
- memory read/write
- plan steps
- tool calls
- tool arguments
- tool outputs
- final response
- approval events
- error events

## 10. 입력 요구사항

Judge Agent는 다음 입력을 받을 수 있어야 한다.

- `transcript.md` 또는 `conversation.json`
- `instructions.md` 또는 instruction bundle
- `tool_calls.json`
- `memory_snapshot.json` 또는 memory files
- `retrieved_context.json`
- `trace.json`
- `expected.json` 또는 fixture
- `baseline_findings.json`
- `rubric.yaml`

## 11. 출력 요구사항

### 11.1 Finding JSON Schema

```json
{
  "id": "JD-2026-001",
  "category": "prompt|tool|context|memory|reasoning|goal|safety|output",
  "metric": "tool_selection_accuracy",
  "severity": "low|medium|high|critical",
  "confidence": 0.0,
  "detection_method": "rule|reference_based_judge|reference_free_judge|pairwise|trace_analysis",
  "location": {
    "type": "message|tool_call|memory_op|trace_step|file|session",
    "ref": "string"
  },
  "evidence": ["string"],
  "expected": "string",
  "actual": "string",
  "root_cause_hypothesis": "string",
  "impact": "string",
  "recommendation": "string",
  "regression_test_suggestion": "string"
}
```

### 11.2 Markdown Report 구조

```markdown
# Judge Agent Drift Report

## Executive Summary
## Overall Drift Score
## Release Gate Recommendation
## Critical / High Findings
## Findings by Drift Category
## Metric Breakdown
## Baseline Comparison
## Root Cause Analysis
## Recommended Remediation
## Regression Fixtures
## Evidence Appendix
## Source Trace References
```

## 12. Scoring

### 12.1 기본 점수

- 100점 만점에서 시작
- Critical: -30
- High: -15
- Medium: -7
- Low: -2
- 동일 category 반복 시 multiplier 적용
- safety/policy 위반은 최소 High 이상
- evidence 없는 항목은 finding이 아니라 hypothesis로 분리

### 12.2 Category Score

각 category별 0~100 점수 제공.

- Prompt Drift Score
- Tool Drift Score
- Context Drift Score
- Memory Drift Score
- Reasoning Drift Score
- Goal Drift Score
- Safety Drift Score
- Output Quality Score

### 12.3 Release Gate

- `pass`: Critical/High 없음, overall score >= 85
- `pass_with_warning`: High 없음, overall score >= 70
- `block`: Critical 존재 또는 High 2개 이상 또는 overall score < 70

## 13. MVP 범위

### 포함

- Local CLI
- Markdown/JSON transcript parser
- Tool call trace parser
- Memory/context snapshot parser
- Drift taxonomy 기반 rule check
- LLM-as-a-Judge rubric 평가
- Structured JSON finding output
- Markdown report generation
- Baseline comparison
- Regression fixture generation

### 제외

- 웹 대시보드
- 실시간 streaming monitoring
- 운영 agent 자동 수정
- 조직 계정/권한 관리
- multi-agent collaboration drift의 고급 분석

## 14. CLI 요구사항

```bash
judge-agent analyze \
  --transcript ./data/session.md \
  --instructions ./data/instructions.md \
  --tools ./data/tool_calls.json \
  --memory ./data/memory_snapshot.json \
  --context ./data/retrieved_context.json \
  --rubric ./rubrics/default.yaml \
  --output ./reports/report.md \
  --json ./reports/findings.json
```

```bash
judge-agent compare \
  --baseline ./reports/baseline.json \
  --current ./reports/current.json \
  --output ./reports/comparison.md
```

```bash
judge-agent fixture \
  --finding JD-2026-001 \
  --output ./fixtures/JD-2026-001.yaml
```

## 15. 개발 마일스톤

### Milestone 1: Metric & Rubric Foundation

- Drift taxonomy 확정
- Metric schema 설계
- Rule checker 인터페이스 구현
- Judge prompt template 설계
- Structured finding schema 구현

### Milestone 2: Trace Parser & Analyzer

- Transcript parser
- Tool trace parser
- Memory/context parser
- Execution trajectory builder
- Evidence locator 구현

### Milestone 3: Drift Detection MVP

- Prompt drift detector
- Tool drift detector
- Context drift detector
- Memory drift detector
- Reasoning drift detector
- Safety drift detector

### Milestone 4: Reports & Regression

- Markdown report
- JSON export
- Baseline comparison
- Release gate
- Regression fixture generator

### Milestone 5: Production Hardening

- Batch analysis
- Redaction
- Cost/latency optimization
- Judge consistency calibration
- Human feedback loop

## 16. 품질 기준

- 모든 finding은 evidence excerpt를 포함해야 한다.
- LLM judge 결과는 schema validation을 통과해야 한다.
- Rule-based로 판단 가능한 것은 LLM judge보다 rule을 우선한다.
- Critical finding은 명확한 정책 위반 또는 2개 이상의 근거를 요구한다.
- Confidence가 낮은 항목은 finding이 아니라 hypothesis로 표시한다.
- Judge prompt와 rubric은 versioning한다.

## 17. 보안 및 개인정보 요구사항

- 민감정보 redaction 옵션 제공
- local-only analysis mode 제공
- 외부 LLM judge 사용 여부 명시
- 리포트 export 전 privacy scan 수행
- memory 내용은 최소 필요 범위만 평가에 사용
- 외부 전송 전 사용자 승인 필요

## 18. 성공 지표

- 수동 리뷰 대비 drift 발견 시간 50% 이상 감소
- High/Critical drift false negative 감소
- Regression release 차단률 향상
- Finding별 actionable recommendation 비율 90% 이상
- 동일 drift 재발률 감소
- Judge result schema parse success rate 99% 이상

## 19. 리스크 및 완화책

### Judge hallucination

완화:

- evidence 필수화
- structured output
- deterministic rule 우선
- confidence 및 hypothesis 분리

### False positive 과다

완화:

- baseline comparison
- severity calibration
- human feedback loop
- metric별 threshold 조정

### Agent trace 부족

완화:

- 최소 trace schema 정의
- trace 없는 경우 output-only 평가로 degradation
- missing observability finding 제공

### 민감정보 노출

완화:

- redaction
- local-only mode
- report privacy scan

## 20. 완료 기준

MVP는 다음 조건을 만족하면 완료로 본다.

- 샘플 transcript/trace를 입력하면 drift finding이 포함된 Markdown 리포트가 생성된다.
- JSON findings가 schema validation을 통과한다.
- Prompt/tool/context/memory/reasoning/safety drift 중 최소 5개 category를 탐지한다.
- 각 finding에 category, metric, severity, confidence, evidence, recommendation이 포함된다.
- baseline 대비 current run 비교가 가능하다.
- regression fixture 초안 생성이 가능하다.
- 개발 가이드와 탐지 지표 문서가 별도로 존재한다.
