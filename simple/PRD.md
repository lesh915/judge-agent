# Simple PRD: LangChain/LangGraph Judge Agent

## 0. Reference Agent 구현 반영 사항 (2026-05-14)

Simple 개발 시작 전 `reference_agent/weblog_agent`가 먼저 구현되었다. 따라서 MVP의 1차 검증 대상과 입력 우선순위를 다음처럼 조정한다.

- 1차 입력: `reference_agent/weblog_agent`가 생성하는 canonical JSONL trace
- 1차 대상 agent: `weblog-react-agent`
- 1차 실행 방식: `run-fixture`, `run-all`, `analyze`, `chat`
- 1차 drift fixture: output contract 위반, wrong endpoint, parse error ignored, validation skipped, metric hallucination
- LangSmith/LangChain generic adapter는 reference JSONL adapter 이후 확장한다.

상세 변경사항은 `simple/REFERENCE_AGENT_IMPLEMENTATION_UPDATE.md`와 `docs/DRIFT_TELEMETRY_INTEGRATION_GUIDE.md`를 기준으로 한다.

## 1. 개요

Simple Judge Agent는 **LangChain/LangGraph로 만들어진 agent**의 실행 trace를 분석하여 agent drift를 탐지, 분석, 리포팅하는 최소 제품이다.

초기 범위는 범용 agent drift 플랫폼이 아니라, LangChain/LangGraph agent에서 발생하는 다음 문제를 빠르게 발견하는 것이다.

- instruction을 따르지 않음
- 필요한 tool을 쓰지 않거나 잘못 씀
- tool argument를 hallucination함
- LangGraph node/edge 실행 흐름이 기대와 다름
- retrieved context를 잘못 사용함
- memory/checkpoint state가 drift를 유발함
- 검증 없이 완료를 선언함

## 2. 대상 범위

### 포함

- LangChain agent
- LangGraph workflow / state graph agent
- LangSmith trace export
- LangChain callback 기반 로그
- JSON/JSONL trace artifact
- Markdown/JSON report 생성

### 제외

- CrewAI, AutoGen, OpenAI Agents SDK 등 다른 framework
- 실시간 운영 대시보드
- multi-tenant SaaS
- 복잡한 alerting 시스템
- agent 자동 수정

## 3. 사용자

- LangChain/LangGraph agent 개발자
- prompt/tool/schema를 관리하는 개발자
- CI에서 agent regression을 막고 싶은 QA 담당자
- LangSmith trace를 보고 문제 원인을 빠르게 알고 싶은 운영자

## 4. 핵심 문제

LangChain/LangGraph agent는 단일 LLM 응답이 아니라 여러 단계의 실행 경로를 가진다.

예:

```text
user input
  -> prompt build
  -> LLM reasoning
  -> tool selection
  -> tool call
  -> tool result interpretation
  -> graph node transition
  -> final response
```

최종 응답만 보면 다음 drift를 놓칠 수 있다.

- 정답은 맞지만 불필요한 tool loop가 있었음
- tool result가 실패했는데 성공처럼 답함
- retrieved document와 다른 내용을 생성함
- LangGraph state에 오래된 값이 남아 잘못된 branch로 감
- 파일 수정 후 read/diff/test 없이 완료 처리함

## 5. 제품 목표

- LangSmith/LangChain/LangGraph trace를 읽어 표준 실행 흐름으로 변환한다.
- prompt/tool/context/memory/graph flow/output drift를 탐지한다.
- 각 finding에 evidence, severity, confidence, recommendation을 포함한다.
- CI에서 baseline 대비 regression을 탐지할 수 있게 한다.
- 개발자가 바로 수정할 수 있는 remediation guide를 제공한다.

## 6. 주요 Drift 유형

## 6.1 Prompt Drift

Agent가 system/developer/user instruction 또는 output format을 지키지 않는 현상.

예:

- JSON으로 답하라고 했지만 markdown으로 답함
- tool 사용 전 확인하라는 instruction을 무시함
- agent role과 다른 답변 태도를 보임

## 6.2 Tool Drift

Agent가 tool을 잘못 선택하거나, argument를 잘못 만들거나, 결과를 잘못 해석하는 현상.

예:

- 검색이 필요한데 검색 tool을 쓰지 않음
- `user_id`를 context 없이 임의 생성
- tool error를 무시하고 성공처럼 답함
- 같은 tool을 반복 호출함

## 6.3 Context Drift

Retriever가 가져온 context를 잘못 사용하거나, 필요한 context를 누락하는 현상.

예:

- retrieved document와 final answer가 충돌함
- 관련 없는 document를 근거로 사용함
- source가 없는 내용을 사실처럼 말함

## 6.4 Memory / State Drift

LangChain memory 또는 LangGraph checkpoint/state가 잘못 사용되는 현상.

예:

- 이전 session의 stale state 사용
- state field가 업데이트되지 않았는데 다음 node가 사용
- memory에 없는 사실을 기억한다고 주장

## 6.5 Graph Flow Drift

LangGraph node/edge 실행이 기대 workflow에서 벗어나는 현상.

예:

- validation node를 건너뜀
- error branch를 타야 하는데 success branch로 이동
- 같은 node를 반복 실행
- human approval node 없이 write/action node로 이동

## 6.6 Completion Drift

완료 조건을 만족하지 않았는데 완료를 선언하는 현상.

예:

- 파일 수정 후 검증 없음
- tool failure 후 재시도/보고 없이 완료
- 요구사항 일부 누락

## 7. MVP 기능

### 7.1 Trace Import

지원 입력:

- Reference Agent JSONL trace (`reference_agent/weblog_agent/traces/*.jsonl`)
- LangGraph custom event JSONL
- LangChain callback JSONL
- LangSmith run export JSON
- manually exported trace JSON

### 7.2 Normalization

모든 입력을 `SimpleAgentRun`으로 변환한다.

```json
{
  "run_id": "string",
  "framework": "langchain|langgraph",
  "user_input": "string",
  "instructions": {},
  "events": [],
  "final_output": "string"
}
```

### 7.3 Detection

초기 detector:

- instruction adherence checker
- tool selection checker
- tool argument checker
- tool error handling checker
- context groundedness checker
- LangGraph node sequence checker
- repeated tool/node loop checker
- missing verification checker

### 7.4 Report

출력:

- `report.md`
- `findings.json`
- `metrics.json`

## 8. CLI 초안

```bash
judge-agent-simple analyze \
  --trace ./trace/langsmith-run.json \
  --framework langgraph \
  --output ./reports/report.md \
  --json ./reports/findings.json
```

```bash
judge-agent-simple compare \
  --baseline ./reports/baseline.json \
  --current ./reports/current.json
```

## 9. Scoring

기본 점수는 100점이다.

- Critical: -30
- High: -15
- Medium: -7
- Low: -2

Release gate:

- `pass`: score >= 85 and no High/Critical
- `warning`: score >= 70 and no Critical
- `block`: Critical exists or score < 70

## 10. 완료 기준

MVP 완료 조건:

- Reference Agent JSONL trace를 입력받아 분석 가능
- WebLog ReAct node/tool/RAG/MCP/chat sequence를 event로 복원 가능
- reference fixture 기준 최소 5개 drift detector 동작
- Markdown report와 JSON findings 생성
- baseline/current 비교 가능
- CI에서 exit code로 pass/block 반환 가능

## LangGraph ReAct Target Agent 기준 추가

초기 Judge Agent는 LangChain/LangGraph 기반 ReAct agent를 1차 대상으로 한다.

대상 agent는 다음 구성을 가진다.

- LLM
- Prompt bundle
- Tools
- RAG retriever
- MCP client/server calls
- LangGraph StateGraph
- ReAct loop
- Validation/finalization node

Judge Agent는 다음을 분석해야 한다.

1. prompt/instruction이 원래 contract와 달라졌는가
2. ReAct step이 필요한 tool/RAG/MCP observation 없이 종료되었는가
3. tool argument가 user input/state에 grounded되어 있는가
4. RAG retrieved context가 task와 관련 있고 report에 올바르게 반영되었는가
5. MCP service metadata가 target endpoint/service와 일치하는가
6. final report가 metric/evidence/RAG/MCP의 성격을 구분하는가
7. validation이 skipped/false-pass 되지 않았는가
