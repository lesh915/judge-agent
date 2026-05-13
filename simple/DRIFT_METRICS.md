# Simple Drift Metrics: LangChain/LangGraph

## 1. 목적

이 문서는 LangChain/LangGraph agent를 대상으로 우선 구현할 drift 탐지 지표를 정의한다.

범용 agent metric이 아니라, LangSmith trace / LangChain callback / LangGraph state transition에서 바로 계산 가능한 지표를 우선한다.

## 2. Metric Categories

초기 metric category는 6개다.

1. Prompt / Instruction
2. Tool Use
3. Context / Retrieval
4. Memory / State
5. LangGraph Flow
6. Final Output / Completion

## 3. Prompt / Instruction Metrics

### instruction_adherence_score

Agent가 주어진 instruction을 따른 정도.

- 범위: 0.0~1.0
- 방법: LLM judge + rule
- evidence: system/developer/user instruction, final output, relevant trace

Drift 예:

- 요구 형식 미준수
- tool 사용 정책 위반
- 사용자 요청 일부 누락

### output_format_compliance

요구된 output format을 지켰는지.

- 방법: deterministic parser
- 예: JSON schema, markdown section, bullet format

### prompt_template_version_present

trace에 prompt template 이름/version이 기록되어 있는지.

- 목적: prompt 변경에 따른 regression 추적
- 누락 시 observability gap

## 4. Tool Use Metrics

### tool_selection_accuracy

선택한 tool이 task에 적절했는지.

계산 방식:

- expected tool이 있으면 exact/set match
- expected tool이 없으면 LLM judge로 necessity 판단

### tool_argument_correctness

tool argument가 schema와 context를 만족하는지.

체크:

- required field 존재
- type 일치
- context/state에 근거한 값인지
- hallucinated value 여부

### tool_error_handling_score

tool error를 적절히 처리했는지.

Drift 예:

- tool error 무시
- 같은 실패 반복
- 실패했는데 성공처럼 응답

### redundant_tool_call_count

같은 목적의 중복 tool 호출 횟수.

Drift 예:

- 동일 query로 search 반복
- 동일 file read 반복
- 같은 tool call loop

### tool_result_grounding_score

final output이 tool result와 일치하는지.

Drift 예:

- tool result와 반대 결론
- 없는 결과를 있다고 주장

## 5. Context / Retrieval Metrics

### retrieval_context_relevance

retriever가 가져온 document/chunk가 user input과 관련 있는지.

### retrieval_context_precision

retrieved chunk 중 관련 있는 chunk의 비율.

```text
relevant_chunks / retrieved_chunks
```

### answer_context_groundedness

final output이 retrieved context에 근거하는지.

Drift 예:

- source 없는 사실 주장
- retrieved context와 충돌
- 낮은 score context를 확정 근거로 사용

### missing_required_context

답변에 필요한 context가 검색되지 않았는지.

- reference fixture가 있을 때 우선 계산
- 없으면 LLM judge로 판단

## 6. Memory / State Metrics

### memory_claim_supported

agent가 “기억한다”고 주장한 내용이 memory/state에 존재하는지.

### state_freshness_score

LangGraph state/checkpoint가 최신인지.

Drift 예:

- 이전 run의 stale state 사용
- update되어야 할 field가 갱신되지 않음

### state_value_grounding

node가 사용한 state 값이 이전 event에서 생성/검증된 값인지.

### memory_update_correctness

저장해야 할 memory를 저장했고, 저장하면 안 되는 내용을 저장하지 않았는지.

## 7. LangGraph Flow Metrics

### node_sequence_correctness

실행된 node 순서가 기대 workflow와 맞는지.

Drift 예:

- validation node skip
- approval node skip
- error branch 대신 success branch 실행

### edge_decision_correctness

conditional edge 선택이 state/tool result와 맞는지.

### node_loop_count

같은 node 반복 횟수.

### graph_completion_path_valid

종료 node까지의 path가 정상 완료 path인지.

### required_checkpoint_present

중요 node 이후 checkpoint/state snapshot이 존재하는지.

## 8. Final Output / Completion Metrics

### task_completion_score

사용자 요청이 완료되었는지.

### verification_coverage

완료 전 필요한 검증을 수행했는지.

예:

- file write 후 read/diff/test
- tool action 후 result 확인
- retrieval 후 source 확인

### final_answer_consistency

final answer가 trace의 실제 실행 결과와 일치하는지.

### hallucinated_completion_claim

실제로 수행하지 않은 일을 완료했다고 말했는지.

## 9. Severity 기준

### Critical

- 승인 없이 외부/파괴적 action 수행
- 민감정보 노출
- 잘못된 tool action으로 실제 피해 가능

### High

- tool failure를 성공으로 보고
- validation/approval node skip
- hallucinated tool argument로 action 수행
- context와 반대되는 답변

### Medium

- 일부 요구사항 누락
- 중복 tool/node loop
- 낮은 groundedness
- state update 누락

### Low

- 경미한 format 위반
- 경미한 장황함
- 영향 낮은 observability gap

## 10. MVP 우선순위

1. `tool_argument_correctness`
2. `tool_error_handling_score`
3. `answer_context_groundedness`
4. `node_sequence_correctness`
5. `verification_coverage`
6. `instruction_adherence_score`
7. `redundant_tool_call_count`
