# Context Engineering 상세 가이드

작성일: 2026-05-15  
위치: `docs/context-engineering-guide.md`

---

## 0. 요약

**Context Engineering(컨텍스트 엔지니어링)**은 LLM 또는 AI Agent가 어떤 정보를 보고, 어떤 순서로 판단하며, 어떤 도구를 사용할지 결정하도록 **컨텍스트 창(context window)에 들어가는 정보의 수집·선택·구조화·압축·격리·검증·운영 방식을 설계하는 방법론**이다.

단순한 Prompt Engineering이 “모델에게 어떻게 말할 것인가”에 가깝다면, Context Engineering은 “모델이 올바르게 일하기 위해 어떤 지식, 기억, 도구, 상태, 예시, 제약, 출력 형식을 언제/어떻게 제공할 것인가”를 다룬다.

핵심 관점은 다음과 같다.

1. LLM의 컨텍스트 창은 무한하지 않다.
2. 더 많은 컨텍스트가 항상 더 좋은 답을 만들지는 않는다.
3. 모델 성능은 모델 자체뿐 아니라, 추론 시점에 제공되는 정보의 품질·구조·순서·충돌 여부에 크게 좌우된다.
4. 에이전트는 장기 작업을 수행하며 도구 호출 결과, 중간 계획, 오류, 요약, 기억이 누적되므로 컨텍스트 관리가 곧 신뢰성이다.
5. 좋은 Context Engineering은 RAG, Memory, Tool Use, Multi-Agent, Workflow, Evaluation, Observability까지 포괄한다.

LangChain은 Context Engineering을 “에이전트 궤적의 각 단계에서 컨텍스트 창을 딱 필요한 정보로 채우는 예술이자 과학”으로 설명한다. 또한 공통 전략을 **Write, Select, Compress, Isolate** 네 가지로 분류한다. Anthropic은 효과적인 에이전트 구축에서 “가장 단순한 해법부터 시작하고, 필요할 때만 복잡도를 늘리라”고 권고하며, LLM에 retrieval, tools, memory를 결합한 **augmented LLM**을 기본 빌딩 블록으로 본다. arXiv의 2025년 Survey 논문은 Context Engineering을 prompt design을 넘어선 “LLM을 위한 information payload의 체계적 최적화”로 정의하고, Retrieval/Generation, Processing, Management 및 RAG, Memory, Tool-integrated Reasoning, Multi-Agent 시스템으로 분류한다.

---

## 1. 왜 Context Engineering이 중요한가

### 1.1 LLM은 현재 컨텍스트만 보고 추론한다

LLM은 학습된 파라미터에 지식을 저장하고 있지만, 실제 응답 생성 시에는 현재 요청에 포함된 다음 정보들을 중심으로 답한다.

- System / Developer / User instructions
- 이전 대화 기록
- 검색 또는 RAG로 가져온 문서
- 도구 목록과 도구 설명
- 도구 호출 결과
- 메모리에서 선택된 사용자 선호/사실/절차
- 예시 few-shot
- 출력 형식 스키마
- 안전 정책 또는 비즈니스 규칙
- 현재 작업 상태

이 모든 것이 모델의 “작업 메모리”인 context window를 차지한다. 따라서 컨텍스트 창에 무엇이 들어가느냐가 모델의 실제 행동을 결정한다.

### 1.2 큰 컨텍스트 창만으로는 충분하지 않다

최근 모델들은 수십만~백만 토큰 수준의 긴 컨텍스트를 지원하지만, 긴 컨텍스트가 자동으로 더 좋은 결과를 보장하지 않는다. Drew Breunig는 긴 컨텍스트의 실패 양상을 네 가지로 정리한다.

1. **Context Poisoning**: 환각이나 잘못된 정보가 컨텍스트에 들어가 이후 추론을 오염시킨다.
2. **Context Distraction**: 너무 긴 컨텍스트 때문에 모델이 학습된 일반 능력보다 과거 내용에 과도하게 끌린다.
3. **Context Confusion**: 불필요한 문서, 도구, 지시가 모델을 헷갈리게 한다.
4. **Context Clash**: 컨텍스트 안의 정보들이 서로 충돌해 모델이 잘못된 전제를 따른다.

즉, “많이 넣기”가 아니라 “필요한 것을, 올바른 형태로, 올바른 시점에 넣기”가 중요하다.

### 1.3 에이전트에서는 컨텍스트가 더 빨리 망가진다

단발성 Q&A보다 에이전트 작업은 컨텍스트 관리가 훨씬 어렵다.

- 여러 단계의 계획과 실행이 누적된다.
- 도구 호출 결과가 길고 지저분하다.
- 오류 메시지, 로그, 검색 결과가 반복적으로 들어온다.
- 중간 추론이나 오래된 계획이 현재 상태와 충돌할 수 있다.
- 긴 작업에서 처음 목표가 잊히거나 왜곡될 수 있다.
- 여러 하위 에이전트가 생성한 결과를 합쳐야 한다.

Anthropic의 multi-agent research system 사례에서도 연구 에이전트는 lead agent가 계획을 memory에 저장하고, subagent들이 병렬 검색 후 결과를 요약해 lead agent에게 반환한다. 이 구조는 각 subagent가 별도 context window를 사용해 탐색하고, 최종적으로 중요한 정보만 압축해 공유한다는 점에서 Context Engineering의 대표적 예시다.

---

## 2. Context Engineering의 정의

### 2.1 실무적 정의

Context Engineering은 다음을 설계·운영하는 일이다.

> LLM/Agent가 목표를 달성하기 위해 필요한 정보를 외부 세계에서 가져오고, 장기/단기 기억에 저장하고, 현재 작업에 맞게 선택하고, 중복·충돌·노이즈를 줄이고, 안전하고 검증 가능한 형태로 모델에게 제공하는 전체 시스템.

### 2.2 Prompt Engineering과의 차이

| 구분 | Prompt Engineering | Context Engineering |
|---|---|---|
| 핵심 질문 | 어떻게 말하면 모델이 잘 답할까? | 모델이 잘 답하기 위해 무엇을 알고 있어야 할까? |
| 범위 | 지시문, 예시, 출력 형식 | 지시문 + 검색 + 메모리 + 도구 + 상태 + 평가 + 압축 + 보안 |
| 단위 | 하나의 프롬프트 | 전체 정보 파이프라인/아키텍처 |
| 주요 기술 | role prompt, few-shot, CoT, ReAct | RAG, memory, tool selection, context compression, state management, multi-agent isolation |
| 실패 원인 | 지시가 모호함 | 정보 누락, 정보 과다, 충돌, 오래된 기억, 잘못된 검색, 도구 남발 |
| 산출물 | prompt template | context policy, retrieval pipeline, memory schema, tool contract, eval set, observability |

Weaviate는 prompt engineering을 “질문을 어떻게 하느냐”, context engineering을 “모델이 답하기 전에 올바른 교재, 계산기, 이전 노트에 접근하도록 만드는 것”에 비유한다.

### 2.3 Context Engineering과 RAG의 관계

RAG(Retrieval-Augmented Generation)는 Context Engineering의 일부다.

- RAG는 외부 문서를 검색해 컨텍스트에 넣는 기술이다.
- Context Engineering은 RAG뿐 아니라, 검색 질의 생성, 문서 chunking, reranking, 메모리 선택, 도구 설명 관리, 대화 요약, 컨텍스트 압축, 하위 에이전트 분리, 출력 검증까지 포함한다.

따라서 모든 RAG는 Context Engineering의 한 구현이 될 수 있지만, 모든 Context Engineering이 RAG는 아니다.

---

## 3. 컨텍스트의 구성 요소

실무에서는 컨텍스트를 다음 계층으로 나누어 관리하면 좋다.

### 3.1 Instruction Context

모델의 역할, 규칙, 우선순위, 금지사항, 출력 형식 등을 담는다.

예시:

```text
You are a customer-support triage agent.
Priority:
1. Safety and privacy
2. Correct classification
3. Concise answer
Never issue refunds directly. Escalate refund requests above $100.
Return JSON matching the schema.
```

관리 포인트:

- 항상 들어가야 하는 core instruction과 상황별 instruction을 분리한다.
- 충돌 가능성이 있는 지시는 우선순위를 명시한다.
- 긴 정책 문서는 요약본 + 필요 시 원문 검색 방식으로 제공한다.

### 3.2 User / Task Context

사용자의 현재 요청, 목표, 제약, 성공 기준이다.

예시:

```json
{
  "task": "경쟁사 리서치 보고서 작성",
  "deadline": "오늘 18:00",
  "audience": "CEO와 제품팀",
  "format": "핵심 요약 + 표 + 출처",
  "constraints": ["한국어", "출처 필수", "추측 금지"]
}
```

관리 포인트:

- 모호한 요청은 query augmentation으로 명확히 재작성한다.
- 목표, 독자, 형식, 제약, 완료 기준을 별도 필드로 분리한다.

### 3.3 Knowledge Context

외부 문서, DB, 웹 검색 결과, 내부 지식베이스, 코드베이스 등이다.

관리 포인트:

- 원문 그대로 넣지 말고, 관련성 높은 chunk를 선별한다.
- 출처, 최신성, 신뢰도, 권한을 함께 보관한다.
- 문서 간 충돌을 감지한다.
- 인용 가능한 답변이 필요하면 chunk id 또는 URL을 유지한다.

### 3.4 Memory Context

과거 대화, 사용자 선호, 프로젝트 결정사항, 반복 작업 규칙 등 장기적으로 재사용되는 정보다.

메모리 유형:

1. **Semantic memory**: 사실/개념. 예: “사용자는 Asia/Seoul 시간대를 사용한다.”
2. **Episodic memory**: 과거 사건/예시. 예: “지난번 PRD는 docs/PRD-agent-folder-execution.md에 저장했다.”
3. **Procedural memory**: 절차/선호 방식. 예: “문서는 한국어로, 상세하게, 출처 포함.”

관리 포인트:

- 메모리는 자동 주입하지 말고 관련성 기반으로 선택한다.
- 민감 정보는 별도 권한과 만료 정책을 둔다.
- 오래된 메모리는 decay 또는 review를 적용한다.
- 사용자에게 불쾌한 “뜻밖의 기억 주입”을 피한다.

### 3.5 Tool Context

모델이 사용할 수 있는 함수/API/도구의 이름, 설명, 입력 스키마, 제약이다.

관리 포인트:

- 모든 도구를 항상 넣지 않는다.
- 현재 작업에 필요한 도구만 선택한다.
- 도구 설명은 짧고 구체적으로 작성한다.
- 위험 도구는 승인 절차와 함께 제공한다.
- 도구 결과는 원문과 요약을 분리한다.

### 3.6 State Context

현재 workflow의 상태, 진행 단계, 중간 산출물, 오류, retry count 등이다.

예시:

```json
{
  "workflow": "invoice_processing",
  "step": "validate_vendor",
  "attempt": 2,
  "validated_fields": ["vendor_name", "invoice_date"],
  "missing_fields": ["tax_id"],
  "last_error": "OCR confidence below threshold"
}
```

관리 포인트:

- 대화 로그 전체보다 구조화된 state를 우선한다.
- state는 idempotent하게 저장해 pause/resume이 가능하게 한다.
- LLM에게 필요한 state만 노출한다.

### 3.7 Output Contract Context

모델이 어떤 형식으로 답해야 하는지 정의한다.

예시:

```json
{
  "type": "object",
  "required": ["decision", "reason", "next_action"],
  "properties": {
    "decision": {"enum": ["approve", "reject", "needs_review"]},
    "reason": {"type": "string"},
    "next_action": {"type": "string"}
  }
}
```

관리 포인트:

- 후속 시스템이 소비할 출력은 JSON schema 또는 typed model로 강제한다.
- 사람이 읽을 답변과 기계가 읽을 structured output을 분리한다.

---

## 4. 핵심 방법론: Write, Select, Compress, Isolate

LangChain의 Context Engineering 분류를 실무형으로 확장하면 다음과 같다.

## 4.1 Write: 컨텍스트를 외부에 기록하기

Write는 현재 context window 밖에 정보를 저장해 나중에 재사용할 수 있게 하는 전략이다.

### 대상

- scratchpad
- 작업 계획
- 중간 결과
- 사용자 선호
- 프로젝트 결정사항
- 검색 결과 요약
- 실패 원인
- 장기 메모리
- 체크포인트 state

### 왜 필요한가

컨텍스트 창은 제한적이다. 모든 것을 계속 들고 있으면 비용과 지연이 증가하고, 오래된 정보가 새 판단을 방해한다. 대신 중요한 정보만 외부 저장소에 쓰고, 필요할 때 선택적으로 가져온다.

### 구현 방식

1. **파일 기반 scratchpad**
   - 예: `scratchpad.md`, `notes.json`, `agent/state.json`
   - 장점: 단순하고 디버깅 쉬움
   - 단점: 검색/권한/동시성 관리 필요

2. **런타임 state object**
   - 예: LangGraph `StateGraph`의 state
   - 장점: workflow 단계별로 필요한 state만 전달 가능
   - 단점: 프레임워크 의존성

3. **Checkpoint store**
   - pause/resume, fault tolerance에 적합

4. **Vector DB / Graph DB memory**
   - 의미 검색, 관계 기반 검색에 적합

5. **Relational DB**
   - 사용자 프로필, 작업 기록, 권한, 감사 로그에 적합

### 예시: 파일 scratchpad

```markdown
# Research Scratchpad

## Goal
Context Engineering 방법론 문서 작성

## Decisions
- RAG는 Context Engineering의 일부로 설명한다.
- LangChain의 write/select/compress/isolate 분류를 핵심 축으로 사용한다.

## Open Questions
- 실제 구현 예시는 Python pseudo-code로 제공한다.

## Sources to cite
- LangChain context engineering blog
- Anthropic building effective agents
- arXiv survey 2507.13334
```

### 주의점

- scratchpad에 환각이 들어가면 이후 추론을 오염시킬 수 있다.
- 기록할 때 provenance/source를 함께 저장해야 한다.
- “확인된 사실”과 “가설/추측”을 분리해야 한다.

---

## 4.2 Select: 필요한 컨텍스트를 선택하기

Select는 외부에 있는 정보 중 현재 작업에 필요한 것만 context window에 넣는 전략이다.

### 선택 대상

- 관련 문서 chunk
- 관련 메모리
- 필요한 도구 목록
- 현재 workflow state 중 필요한 필드
- few-shot 예시
- 정책 문서 중 적용되는 조항

### 선택 기준

1. **Relevance**: 현재 질문과 관련 있는가?
2. **Recency**: 최신 정보인가?
3. **Authority**: 신뢰 가능한 출처인가?
4. **Specificity**: 일반론보다 현재 사례에 구체적인가?
5. **Diversity**: 한쪽 관점만 가져오지 않았는가?
6. **Non-conflict**: 다른 컨텍스트와 충돌하지 않는가?
7. **Permission**: 현재 사용자/작업에서 접근 가능한가?
8. **Token budget**: 넣을 가치가 토큰 비용보다 큰가?

### 검색 파이프라인 예시

```text
User Query
  ↓
Query Understanding / Augmentation
  ↓
Candidate Retrieval
  - BM25 keyword search
  - vector similarity search
  - metadata filter
  - graph traversal
  ↓
Reranking
  - cross encoder
  - LLM relevance judge
  - recency/source score
  ↓
Deduplication / Conflict Check
  ↓
Context Packing
  - 가장 중요한 chunk부터
  - source id 유지
  - token budget 내 배치
  ↓
LLM Call
```

### 예시: 도구 선택

나쁜 방식:

```text
모든 도구 120개를 system prompt에 넣는다.
```

좋은 방식:

```text
1. 사용자 요청을 분류한다.
2. 요청이 “일정 확인”이면 calendar_search, calendar_create만 노출한다.
3. 요청이 “문서 요약”이면 file_read, vector_search만 노출한다.
4. 결제/삭제/외부 발송 도구는 명시 승인 전까지 숨긴다.
```

### 주의점

- 기억을 너무 적극적으로 가져오면 사용자에게 감시받는 느낌을 줄 수 있다.
- 검색 결과가 비슷한 문서로만 채워지면 관점이 좁아진다.
- 도구 설명이 많으면 Context Confusion이 발생한다.

---

## 4.3 Compress: 컨텍스트를 압축하기

Compress는 긴 정보에서 현재 작업에 필요한 핵심만 남기는 전략이다.

### 압축 대상

- 긴 대화 기록
- 도구 호출 결과
- 검색 결과 여러 개
- 로그/스택트레이스
- 코드 diff
- 회의록
- 하위 에이전트 결과

### 압축 방법

1. **Extractive summary**
   - 원문 문장 일부를 그대로 추출
   - 인용/법무/정확성이 중요한 경우 적합

2. **Abstractive summary**
   - 의미를 새 문장으로 요약
   - 일반 보고서/상황 요약에 적합
   - 환각 위험 있음

3. **Structured summary**
   - JSON/표/필드 형태로 요약
   - workflow state로 쓰기 좋음

4. **Hierarchical summary**
   - chunk 요약 → 섹션 요약 → 전체 요약
   - 긴 문서/대규모 검색 결과에 적합

5. **Delta summary**
   - 이전 상태 대비 바뀐 것만 기록
   - 장기 대화나 반복 작업에 적합

6. **Error compaction**
   - 긴 오류 로그에서 핵심 원인, 재현 조건, 다음 시도만 남김
   - 12-Factor Agents의 “Compact Errors into Context Window”와 연결됨

### 예시: 도구 결과 압축

원본:

```text
검색 결과 20개, 각 페이지 본문 10,000자, 중복 문단 다수...
```

압축 후:

```json
{
  "query": "Context Engineering open source",
  "key_findings": [
    "LangChain은 write/select/compress/isolate 네 가지 전략을 예제로 제공한다.",
    "MCP는 AI 앱과 외부 시스템을 연결하는 open-source standard다.",
    "12-Factor Agents는 own your context window, compact errors 등을 원칙으로 제시한다."
  ],
  "sources": [
    {"title": "LangChain context_engineering", "url": "https://github.com/langchain-ai/context_engineering"},
    {"title": "MCP introduction", "url": "https://modelcontextprotocol.io/introduction"},
    {"title": "12-factor-agents", "url": "https://github.com/humanlayer/12-factor-agents"}
  ],
  "uncertainties": []
}
```

### 압축 품질 기준

- 중요한 결정과 근거가 남아 있는가?
- 출처가 유지되는가?
- 확인된 사실과 추론이 구분되는가?
- 오래된 정보가 현재 정보처럼 보이지 않는가?
- 다음 행동에 필요한 정보가 충분한가?

---

## 4.4 Isolate: 컨텍스트를 격리하기

Isolate는 서로 다른 작업, 역할, 도구, 권한, 정보 범위를 분리해 컨텍스트 오염을 줄이는 전략이다.

### 격리 대상

- 하위 작업별 context window
- 역할별 instruction
- 민감 데이터 접근 범위
- 도구 권한
- 실험적 추론과 최종 답변
- 검색/코딩/검증 에이전트

### 왜 필요한가

하나의 거대한 컨텍스트에 모든 정보와 도구를 넣으면 다음 문제가 생긴다.

- irrelevant context가 판단을 흐린다.
- 도구가 너무 많아 잘못된 도구를 호출한다.
- 하위 작업의 가설이 최종 결론을 오염시킨다.
- 민감 정보가 필요 없는 단계에 노출된다.
- 여러 목표가 충돌한다.

### 예시: 연구 multi-agent

```text
Lead Researcher
  - 사용자 질문 이해
  - 리서치 계획 수립
  - Subagent에게 구체적 작업 위임
  - 결과 통합 및 출처 검증

Subagent A: 시장 규모 조사
  - 웹 검색 도구만 사용
  - 시장 규모 수치와 출처만 반환

Subagent B: 경쟁사 제품 조사
  - 웹 검색 + 표 생성
  - 기능 비교만 반환

Citation Agent
  - 최종 문장별 출처 위치 확인
  - citation 누락 검출
```

각 agent는 별도 context window를 사용하고, lead agent는 원문 전체가 아니라 압축된 결과만 받는다. Anthropic은 multi-agent research system에서 subagent들이 병렬로 탐색하고 중요한 토큰만 lead agent에게 반환하는 구조가 연구 작업에 효과적이라고 설명한다.

### 격리 설계 원칙

- 하위 에이전트에게 목표, 범위, 출력 형식을 명확히 준다.
- 하위 에이전트가 볼 필요 없는 메모리와 도구는 숨긴다.
- 최종 통합 단계에서 출처와 충돌을 검증한다.
- 병렬화 가치가 큰 작업에만 multi-agent를 쓴다.
- 코딩처럼 강한 상호의존이 있는 작업은 무조건 multi-agent가 유리하지 않다.

---

## 5. Context Engineering 절차

아래 절차는 실제 프로젝트에 적용하기 좋은 표준 흐름이다.

## 5.1 1단계: 목표와 성공 기준 정의

먼저 LLM이 해결해야 하는 문제를 명확히 한다.

체크리스트:

- 사용자는 누구인가?
- 입력은 무엇인가?
- 출력은 무엇인가?
- 정답/성공을 어떻게 판단하는가?
- 실시간성/최신성이 필요한가?
- 출처가 필요한가?
- 비용/지연 한계는?
- 실패 시 fallback은?
- 사람이 승인해야 하는 단계는?

예시:

```yaml
use_case: 고객 문의 자동 분류
input: 고객 이메일 본문
output: category, urgency, suggested_reply, escalation_required
success_metric:
  - category accuracy >= 90%
  - high-risk escalation recall >= 98%
constraints:
  - 개인정보를 외부 검색에 사용 금지
  - 환불 실행은 사람이 승인
  - 응답은 한국어
```

## 5.2 2단계: 컨텍스트 인벤토리 작성

모델이 사용할 수 있는 정보 자산을 나열한다.

| 컨텍스트 | 예시 | 저장 위치 | 최신성 | 권한 | 주입 방식 |
|---|---|---|---|---|---|
| 정책 | 환불 정책 | Notion/DB | 월간 | 내부 | RAG |
| 사용자 선호 | 말투/언어 | profile DB | 상시 | 본인 | memory select |
| 대화 기록 | 최근 상담 | ticket DB | 실시간 | 담당자 | summary |
| 도구 | refund API | internal API | 실시간 | 승인 필요 | selected tool |
| 예시 | 과거 분류 사례 | eval dataset | 고정 | 내부 | few-shot |

## 5.3 3단계: 컨텍스트 분류와 우선순위 설정

컨텍스트를 필수/선택/금지로 나눈다.

```yaml
always_include:
  - core system instruction
  - output schema
  - safety rules
include_when_relevant:
  - policy chunks
  - user memory
  - previous ticket summaries
  - domain examples
never_include:
  - unrelated user private data
  - raw secrets/API keys
  - obsolete policy versions
  - unverified hallucinated notes
```

## 5.4 4단계: Query Understanding / Augmentation 설계

사용자 요청은 대개 불완전하다. 검색과 도구 호출을 위해 의도를 재구성해야 한다.

예시:

사용자 입력:

```text
지난번 거랑 비슷하게 정리해줘
```

증강된 작업 정의:

```json
{
  "intent": "document_generation",
  "reference": "previous document style in docs/",
  "topic": "unknown",
  "missing_info": ["topic"],
  "action": "ask_clarifying_question_if_topic_not_in_context"
}
```

검색용 query는 또 다를 수 있다.

```json
{
  "semantic_query": "context engineering methodology RAG memory tool use multi-agent examples",
  "keyword_query": "Context Engineering write select compress isolate RAG memory agents",
  "filters": {
    "language": ["en", "ko"],
    "source_type": ["docs", "paper", "github", "engineering blog"]
  }
}
```

## 5.5 5단계: Retrieval 설계

검색 대상에 따라 retrieval 전략이 달라진다.

### 문서 검색

- chunk size: 너무 작으면 맥락 손실, 너무 크면 노이즈 증가
- overlap: 문단 경계 보존
- metadata: source, date, author, version, permission
- hybrid search: keyword + vector
- reranking: cross-encoder 또는 LLM judge
- citation: chunk id 유지

### 코드 검색

- symbol/function 단위 chunking
- call graph, import graph 활용
- README/테스트/설정 파일 우선 검색
- 변경 전 관련 테스트 검색

### 메모리 검색

- semantic/episodic/procedural memory 분리
- recency와 relevance 함께 고려
- 민감 정보 권한 확인
- 자동 주입 전 사용자 기대와 맞는지 고려

### 도구 검색

- tool registry 구축
- tool description embedding
- intent별 allowlist
- 위험도 등급 부여

## 5.6 6단계: Context Packing 설계

선택된 컨텍스트를 모델에 넣는 순서와 구조를 설계한다.

권장 순서 예시:

```text
1. Core instruction / role
2. Safety and priority rules
3. Task objective and success criteria
4. Output schema
5. Relevant state
6. Selected memories
7. Retrieved knowledge with citations
8. Available tools
9. User request
```

주의:

- 가장 중요한 지시를 노이즈 사이에 묻히게 하지 않는다.
- 출처별 구분자를 명확히 한다.
- 오래된 정보와 최신 정보를 표시한다.
- 충돌하는 정보가 있으면 “conflict detected”로 별도 전달한다.

## 5.7 7단계: Tool Use 설계

도구는 context를 확장하지만 동시에 위험을 만든다.

도구 설계 체크리스트:

- 도구 이름이 명확한가?
- 설명은 짧고 오해가 없는가?
- 입력 스키마가 엄격한가?
- side effect가 있는가?
- 사용자 승인이 필요한가?
- 실패 시 오류가 구조화되어 반환되는가?
- 도구 결과가 너무 길면 요약하는가?

예시 tool contract:

```json
{
  "name": "search_policy",
  "description": "Search current internal customer policy documents. Use only for policy questions.",
  "input_schema": {
    "type": "object",
    "required": ["query", "policy_area"],
    "properties": {
      "query": {"type": "string"},
      "policy_area": {"enum": ["refund", "privacy", "shipping", "account"]}
    }
  },
  "side_effect": false,
  "returns": "List of policy chunks with source_id and effective_date"
}
```

## 5.8 8단계: Memory 정책 설계

메모리는 강력하지만 위험하다.

정책 예시:

```yaml
memory_policy:
  write:
    allow:
      - stable user preferences
      - explicit decisions
      - project conventions
    deny:
      - passwords
      - one-off transient facts
      - unverified assumptions
  read:
    strategy: relevance_and_recency
    max_items: 5
    require_source: true
  update:
    review_old_memories_after_days: 90
    conflict_resolution: prefer_latest_explicit_user_statement
```

## 5.9 9단계: Compression 정책 설계

언제 요약할지 기준을 둔다.

예시:

```yaml
compression_policy:
  conversation:
    trigger: token_count > 60000
    method: structured_summary
    preserve:
      - user goal
      - decisions
      - open tasks
      - constraints
      - source links
  tool_outputs:
    trigger: output_tokens > 4000
    method: extractive_then_abstractive
    preserve:
      - errors
      - ids
      - citations
      - exact values
  logs:
    trigger: always
    method: error_compaction
```

## 5.10 10단계: Evaluation 설계

Context Engineering은 평가 없이는 개선하기 어렵다.

평가 항목:

- 정답성
- 출처 정확성
- 관련 없는 컨텍스트 사용 여부
- 오래된 정보 사용 여부
- 도구 선택 정확도
- 메모리 선택 적절성
- 비용/지연
- hallucination rate
- refusal/escalation 적절성
- context conflict 처리

테스트셋 유형:

1. 정상 사례
2. 모호한 요청
3. 문서에 답이 없는 사례
4. 오래된 문서와 최신 문서가 충돌하는 사례
5. irrelevant memory가 검색되는 사례
6. 도구가 필요 없는 사례
7. 위험 도구 승인이 필요한 사례
8. 긴 로그/긴 대화 압축 사례

## 5.11 11단계: Observability 설계

운영에서는 “왜 모델이 이런 답을 했는지” 추적해야 한다.

로그해야 할 것:

- 최종 prompt/context 구성 요약
- 검색 query
- 선택된 chunk id와 score
- 제외된 상위 후보
- 사용된 memory id
- 노출된 tool list
- tool call input/output
- compression 전후 token 수
- 모델 출력
- 평가 결과
- 사용자 피드백

주의:

- 개인정보와 secret은 마스킹한다.
- 전체 prompt 저장은 보안 정책에 맞게 제한한다.
- 재현 가능한 trace id를 부여한다.

---

## 6. 대표 아키텍처 패턴

## 6.1 Simple Augmented LLM

가장 기본적인 구조다.

```text
User Input
  ↓
Prompt Template + Few-shot
  ↓
LLM
  ↓
Answer
```

적합한 경우:

- 외부 지식이 거의 필요 없음
- 짧은 작업
- 정형 변환/분류

한계:

- 최신 정보/내부 정보 접근 불가
- 장기 기억 없음

## 6.2 RAG Pipeline

```text
User Input
  ↓
Query Rewrite
  ↓
Retriever
  ↓
Reranker
  ↓
Context Packing
  ↓
LLM
  ↓
Answer with Citations
```

적합한 경우:

- 문서 기반 Q&A
- 사내 지식 검색
- 정책/매뉴얼 답변

주의:

- chunking과 reranking 품질이 중요하다.
- 검색 결과가 없을 때 “모른다”고 답해야 한다.
- citation을 유지해야 한다.

## 6.3 Agent with Tools

```text
User Goal
  ↓
Planner / LLM
  ↓
Tool Selection
  ↓
Tool Call
  ↓
Observation
  ↓
Next Decision Loop
  ↓
Final Answer
```

적합한 경우:

- 여러 API/DB를 사용해야 하는 작업
- 동적으로 다음 단계가 결정되는 작업
- 일정 확인, 코드 수정, 리서치 등

주의:

- 도구 결과가 context를 빠르게 키운다.
- loop 종료 조건이 필요하다.
- side-effect 도구는 승인 gate가 필요하다.

## 6.4 Workflow + LLM Steps

Anthropic은 workflow와 agent를 구분한다.

- Workflow: 미리 정의된 코드 경로를 따라 LLM과 도구가 실행됨
- Agent: LLM이 동적으로 프로세스와 도구 사용을 결정함

많은 production 시스템은 완전 자율 agent보다 workflow 안에 LLM step을 넣는 방식이 더 안정적이다.

예시:

```text
Email Received
  ↓
LLM classify intent
  ↓
if refund_request:
    retrieve refund policy
    draft response
    if amount > 100:
        human approval
    else:
        send via workflow
else if tech_support:
    retrieve troubleshooting docs
    draft steps
```

## 6.5 Multi-Agent with Context Isolation

```text
Lead Agent
  ├─ Research Agent A
  ├─ Research Agent B
  ├─ Code Agent
  └─ Critic/Citation Agent
  ↓
Synthesis
```

적합한 경우:

- 병렬 탐색이 유리한 리서치
- 서로 독립적인 하위 문제
- 단일 context window를 초과하는 정보량

주의:

- 비용이 크게 증가한다.
- 조정 복잡도가 높다.
- 하위 agent 출력 형식이 엄격해야 한다.

---

## 7. Context Engineering과 관련된 오픈소스/도구

## 7.1 LangChain / LangGraph

- URL: https://github.com/langchain-ai/langchain
- URL: https://github.com/langchain-ai/langgraph
- Context Engineering 예제: https://github.com/langchain-ai/context_engineering

주요 용도:

- agent workflow 구성
- state graph
- tool calling
- checkpointing
- memory store
- RAG pipeline
- context write/select/compress/isolate 예제

LangChain의 `context_engineering` 저장소는 다음 notebook을 제공한다.

- `1_write_context.ipynb`: 외부에 context 저장
- `2_select_context.ipynb`: 관련 context 검색/선택
- `3_compress_context.ipynb`: 요약과 압축
- `4_isolate_context.ipynb`: context 격리

## 7.2 LlamaIndex

- URL: https://github.com/run-llama/llama_index

주요 용도:

- 문서 ingestion
- indexing
- retrieval
- query engine
- agent와 tool 연동
- 다양한 vector store 통합

Context Engineering 관점:

- knowledge context를 구조화하고 검색하는 데 강점
- 문서 기반 RAG와 데이터 커넥터에 유용

## 7.3 DSPy

- URL: https://github.com/stanfordnlp/dspy

주요 용도:

- LLM 프로그램을 declarative하게 작성
- prompt와 pipeline을 자동 최적화
- retrieval + generation 모듈화

Context Engineering 관점:

- prompt를 수동으로 계속 고치는 대신, task metric에 맞게 context/prompt pipeline을 최적화하는 접근에 유용

## 7.4 Haystack

- URL: https://github.com/deepset-ai/haystack

주요 용도:

- production RAG pipeline
- retriever/ranker/generator 조합
- document store 통합

Context Engineering 관점:

- retrieval, reranking, pipeline observability에 적합

## 7.5 Weaviate

- URL: https://github.com/weaviate/weaviate
- Context Engineering 글: https://weaviate.io/blog/context-engineering

주요 용도:

- vector database
- hybrid search
- semantic retrieval
- agent memory / RAG backend

Context Engineering 관점:

- long-term memory와 knowledge retrieval 계층 구현에 적합

## 7.6 Chroma

- URL: https://github.com/chroma-core/chroma

주요 용도:

- 로컬/간단한 vector DB
- 빠른 RAG 프로토타입

## 7.7 Qdrant

- URL: https://github.com/qdrant/qdrant

주요 용도:

- production vector search
- metadata filtering
- hybrid retrieval 구성 가능

## 7.8 FAISS

- URL: https://github.com/facebookresearch/faiss

주요 용도:

- 고성능 similarity search
- 자체 vector index 구축

## 7.9 LanceDB

- URL: https://github.com/lancedb/lancedb

주요 용도:

- embedded vector database
- multimodal/vector data 관리

## 7.10 Model Context Protocol(MCP)

- URL: https://modelcontextprotocol.io/introduction
- GitHub: https://github.com/modelcontextprotocol

MCP는 AI 애플리케이션을 외부 시스템에 연결하기 위한 open-source standard다. 공식 문서는 MCP를 “AI 애플리케이션을 위한 USB-C 포트”에 비유한다.

Context Engineering 관점:

- tool/data source/workflow를 표준 방식으로 연결
- AI 앱이 파일, DB, 검색, 업무 시스템에 접근 가능
- 단, MCP server가 많아질수록 tool context confusion 위험이 커지므로 tool selection이 중요하다.

## 7.11 HumanLayer / 12-Factor Agents

- URL: https://github.com/humanlayer/12-factor-agents
- Blog: https://www.humanlayer.dev/blog/12-factor-agents

주요 원칙 중 Context Engineering과 직접 관련된 것:

- Factor 2: Own your prompts
- Factor 3: Own your context window
- Factor 5: Unify execution state and business state
- Factor 6: Launch/Pause/Resume with simple APIs
- Factor 9: Compact Errors into Context Window
- Factor 10: Small, Focused Agents
- Factor 12: Make your agent a stateless reducer

Context Engineering 관점:

- 프레임워크에 과도하게 맡기지 말고 prompt/context/state/control flow를 소유하라는 실무적 접근

## 7.12 PydanticAI

- URL: https://github.com/pydantic/pydantic-ai

주요 용도:

- typed agent 개발
- structured output
- dependency injection
- tool schema 관리

Context Engineering 관점:

- output contract, tool input schema, state typing을 강하게 관리하는 데 유용

## 7.13 Instructor

- URL: https://github.com/instructor-ai/instructor

주요 용도:

- LLM structured outputs
- Pydantic schema 기반 응답 파싱/검증

Context Engineering 관점:

- “출력 형식” 역시 context의 일부이므로, schema 기반 검증이 중요하다.

## 7.14 Guidance

- URL: https://github.com/guidance-ai/guidance

주요 용도:

- constrained generation
- template-based generation

## 7.15 Semantic Kernel

- URL: https://github.com/microsoft/semantic-kernel

주요 용도:

- enterprise agent orchestration
- planner, memory, connectors

## 7.16 AutoGen

- URL: https://github.com/microsoft/autogen

주요 용도:

- multi-agent conversation framework
- agent collaboration pattern 실험

Context Engineering 관점:

- multi-agent context isolation과 role-specific context 설계 실험에 유용

## 7.17 CrewAI

- URL: https://github.com/crewAIInc/crewAI

주요 용도:

- role-based multi-agent workflow

주의:

- 역할이 늘어날수록 context와 비용이 커지므로, 명확한 task boundary와 output contract가 필요하다.

## 7.18 OpenAI Evals / Ragas / DeepEval

- OpenAI Evals: https://github.com/openai/evals
- Ragas: https://github.com/explodinggradients/ragas
- DeepEval: https://github.com/confident-ai/deepeval

주요 용도:

- RAG/LLM 평가
- faithfulness, answer relevancy, context precision/recall 등 측정

Context Engineering 관점:

- retrieval 품질과 context 사용 품질을 수치로 추적하기 위해 필요

## 7.19 Langfuse / Phoenix / OpenTelemetry

- Langfuse: https://github.com/langfuse/langfuse
- Arize Phoenix: https://github.com/Arize-ai/phoenix
- OpenTelemetry: https://github.com/open-telemetry/opentelemetry-collector

주요 용도:

- LLM trace
- prompt/version tracking
- retrieval/tool call observability
- evaluation feedback loop

Context Engineering 관점:

- 어떤 context가 들어갔고 왜 실패했는지 추적하는 데 필수

---

## 8. 실제 예시 1: 문서 기반 Q&A RAG

### 8.1 문제

사내 정책 문서를 기반으로 직원 질문에 답하는 챗봇을 만든다.

요구사항:

- 최신 정책만 사용
- 출처 필수
- 문서에 없으면 모른다고 답함
- 개인정보/권한 제한 준수

### 8.2 컨텍스트 설계

```yaml
always_include:
  - role: internal policy assistant
  - rule: answer only from retrieved documents
  - rule: cite source_id for every claim
  - output_format: markdown with citations
retrieval:
  sources:
    - HR policy docs
    - IT security docs
  filters:
    effective_date: latest
    permission: user_department
  top_k: 20
  rerank_top_k: 5
compression:
  method: extract relevant clauses only
fallback:
  no_context: "문서에서 확인할 수 없습니다. 담당 부서에 문의하세요."
```

### 8.3 Python pseudo-code

```python
from typing import List

class RetrievedChunk:
    def __init__(self, source_id: str, title: str, text: str, score: float, effective_date: str):
        self.source_id = source_id
        self.title = title
        self.text = text
        self.score = score
        self.effective_date = effective_date


def augment_query(user_question: str) -> dict:
    return {
        "semantic_query": user_question,
        "keyword_query": extract_keywords(user_question),
        "intent": classify_intent(user_question),
    }


def retrieve_policy_context(query: dict, user_acl: dict) -> List[RetrievedChunk]:
    candidates = hybrid_search(
        semantic=query["semantic_query"],
        keywords=query["keyword_query"],
        filters={
            "effective": True,
            "department": user_acl["department"],
        },
        top_k=20,
    )
    reranked = rerank(query["semantic_query"], candidates)
    return reranked[:5]


def build_context(question: str, chunks: List[RetrievedChunk]) -> str:
    if not chunks:
        return "NO_RELEVANT_CONTEXT"

    packed = []
    for c in chunks:
        packed.append(
            f"[source_id={c.source_id}; title={c.title}; effective_date={c.effective_date}]\n{c.text}"
        )
    return "\n\n---\n\n".join(packed)


def answer(question: str, user_acl: dict):
    query = augment_query(question)
    chunks = retrieve_policy_context(query, user_acl)
    context = build_context(question, chunks)

    prompt = f"""
You are an internal policy assistant.
Rules:
- Answer only from the provided context.
- If context is insufficient, say you cannot confirm from the documents.
- Cite source_id for every factual claim.

Context:
{context}

Question:
{question}
"""
    return call_llm(prompt)
```

### 8.4 실패 사례와 개선

실패:

- top-k 검색만 사용해 오래된 정책이 검색됨
- 출처 없이 일반 지식으로 답변
- 여러 정책 문서가 충돌했는데 최신 문서 판단 실패

개선:

- metadata `effective_date` 필터 추가
- “문서에 없으면 모른다” 규칙 강화
- source_id를 prompt에 명시
- conflict detection 추가
- eval set에 오래된 정책 vs 최신 정책 충돌 사례 포함

---

## 9. 실제 예시 2: 고객지원 에이전트

### 9.1 문제

고객 이메일을 읽고 다음을 수행한다.

- 문의 유형 분류
- 긴급도 판단
- 관련 정책 검색
- 초안 작성
- 환불/계정삭제 등 위험 작업은 사람 승인 요청

### 9.2 컨텍스트 설계

```yaml
context_layers:
  instruction:
    - customer support triage role
    - privacy rules
    - escalation rules
  user_task:
    - current email
    - customer tier
  memory:
    - previous ticket summary only, if same customer and relevant
  knowledge:
    - selected policy chunks
  tools:
    - search_policy
    - get_customer_orders
    - draft_reply
    - request_human_approval
  hidden_until_approval:
    - issue_refund
    - delete_account
```

### 9.3 Workflow

```text
Email received
  ↓
Classify intent / urgency
  ↓
Retrieve relevant policy
  ↓
Check customer history summary
  ↓
Draft answer
  ↓
If side effect needed:
    request human approval
Else:
    send draft to agent/user for review
```

### 9.4 Structured output

```json
{
  "category": "refund_request",
  "urgency": "medium",
  "customer_sentiment": "frustrated",
  "policy_sources": ["refund_policy_2026_01#section_3"],
  "suggested_reply": "...",
  "requires_human_approval": true,
  "approval_reason": "Refund amount exceeds automatic threshold",
  "next_action": "request_human_approval"
}
```

### 9.5 Context Engineering 포인트

- 고객의 전체 과거 대화를 넣지 않고 summary만 사용한다.
- 환불 실행 도구는 초기에 노출하지 않는다.
- 정책 문서 검색 결과는 최신 버전만 사용한다.
- 감정/긴급도는 분류하되, 과도한 추측을 피한다.
- 승인 전 외부 발송/환불 실행 금지.

---

## 10. 실제 예시 3: 코딩 에이전트

### 10.1 문제

사용자가 “로그인 버그 고쳐줘”라고 요청한다.

코딩 에이전트는 다음 정보를 관리해야 한다.

- 프로젝트 구조
- 관련 파일
- 에러 로그
- 테스트 명령
- 코딩 규칙
- 이전 변경 사항
- git diff
- 실패한 테스트 결과

### 10.2 나쁜 컨텍스트 전략

```text
전체 repository 파일을 모두 context에 넣는다.
모든 테스트 로그를 원문 그대로 누적한다.
실패한 가설과 오래된 계획을 계속 남긴다.
```

문제:

- 비용 증가
- 잘못된 파일 수정
- 오래된 오류에 집착
- context distraction

### 10.3 좋은 컨텍스트 전략

```text
1. 파일 트리와 README를 먼저 읽는다.
2. 로그인 관련 symbol/file만 검색한다.
3. 실패 로그를 핵심 stack trace로 압축한다.
4. 수정 계획을 scratchpad에 기록한다.
5. 변경 후 관련 테스트만 실행한다.
6. 실패하면 error compaction 후 다음 시도를 한다.
7. 최종 답변에는 변경 파일, 테스트 결과, 남은 리스크만 포함한다.
```

### 10.4 Error compaction 예시

원본 로그:

```text
수천 줄의 npm test output...
TypeError: Cannot read properties of undefined (reading 'token')
 at auth/session.ts:47
 at login.test.ts:88
...
```

압축:

```json
{
  "error_type": "TypeError",
  "message": "Cannot read properties of undefined (reading 'token')",
  "location": "auth/session.ts:47",
  "failing_test": "login.test.ts:88 should persist session token",
  "likely_cause": "login response may omit session object on 2FA path",
  "next_attempt": "guard session before reading token and add test for 2FA response"
}
```

---

## 11. 실제 예시 4: 리서치 보고서 multi-agent

### 11.1 문제

“Context Engineering에 대한 상세 문서를 출처와 함께 작성하라.”

### 11.2 아키텍처

```text
Lead Writer
  - 문서 목차 설계
  - 필요한 리서치 질문 분해
  - 출처 통합

Research Agent 1: 개념/방법론
Research Agent 2: 오픈소스/프레임워크
Research Agent 3: 실제 사례/패턴
Citation Agent: 출처 확인
Editor Agent: 한국어 문서화
```

### 11.3 각 agent의 context isolation

Research Agent 1에게는 다음만 준다.

```yaml
task: Context Engineering definitions and methodology
allowed_sources:
  - papers
  - engineering blogs
output_schema:
  - definition
  - key concepts
  - methodology
  - sources
```

Research Agent 2에게는 다음만 준다.

```yaml
task: open-source tools related to Context Engineering
allowed_sources:
  - GitHub
  - official docs
output_schema:
  - name
  - url
  - purpose
  - context_engineering_relevance
```

Lead Writer는 각 결과를 합치되, 원문 전체가 아니라 structured summary만 받는다.

### 11.4 장점

- 병렬로 정보 수집 가능
- 각 agent의 context가 좁아져 혼란 감소
- 출처 확인 전담 가능

### 11.5 단점

- token 비용 증가
- 하위 agent 간 중복 가능
- lead agent의 synthesis 품질이 중요

---

## 12. Context 실패 모드와 대응

## 12.1 Context Poisoning

증상:

- 잘못된 가정이 scratchpad나 summary에 들어간다.
- 이후 단계가 그 가정을 사실처럼 사용한다.

대응:

- 메모리/요약에 confidence와 source를 기록한다.
- 확인되지 않은 내용은 `hypothesis`로 표시한다.
- 중요한 결론 전 source verification을 수행한다.
- summary를 덮어쓰기보다 changelog를 유지한다.

## 12.2 Context Distraction

증상:

- 긴 대화 기록에 끌려 현재 요청을 놓친다.
- 과거 행동을 반복한다.

대응:

- 오래된 로그를 structured summary로 대체한다.
- 현재 목표와 성공 기준을 매 호출에 명시한다.
- irrelevant history를 제거한다.
- token budget threshold를 둔다.

## 12.3 Context Confusion

증상:

- 필요 없는 도구를 호출한다.
- 관련 없는 문서 내용을 답변에 섞는다.

대응:

- tool allowlist를 intent별로 제한한다.
- retrieval 결과를 rerank한다.
- prompt에 “use only relevant context”만 쓰지 말고, 실제로 context를 줄인다.
- few-shot 예시도 너무 많이 넣지 않는다.

## 12.4 Context Clash

증상:

- 문서 A와 B가 서로 다른 정책을 말한다.
- 이전 assistant 답변과 최신 도구 결과가 충돌한다.

대응:

- source priority와 effective_date를 둔다.
- 충돌 감지 시 답변 전에 명시적으로 해결한다.
- 최신 공식 문서를 우선한다.
- 불확실하면 사람 검토로 escalate한다.

## 12.5 Lost-in-the-middle

증상:

- 긴 컨텍스트 중간에 있는 핵심 정보를 놓친다.

대응:

- 핵심 정보는 앞/뒤에 배치한다.
- structured summary를 앞에 둔다.
- 긴 문서는 질의별 관련 chunk만 제공한다.

## 12.6 Tool Overload

증상:

- 도구가 너무 많아 잘못된 도구를 선택한다.

대응:

- tool retrieval / dynamic tool selection
- task별 tool groups
- 위험도별 tool exposure
- 도구 설명 간 중복 제거

## 12.7 Memory Overreach

증상:

- 사용자가 원하지 않는 과거 정보를 끌어온다.
- 민감 정보가 불필요한 답변에 섞인다.

대응:

- memory relevance threshold 강화
- private memory는 explicit need가 있을 때만 사용
- memory provenance 표시
- 사용자에게 memory 삭제/수정 가능성 제공

---

## 13. 운영 체크리스트

### 13.1 설계 체크리스트

- [ ] 사용 사례와 성공 기준이 명확한가?
- [ ] context inventory가 작성되었는가?
- [ ] always/include_when_relevant/never_include가 구분되었는가?
- [ ] retrieval source와 권한 정책이 정의되었는가?
- [ ] memory read/write 정책이 있는가?
- [ ] tool exposure 정책이 있는가?
- [ ] output schema가 있는가?
- [ ] compression trigger가 있는가?
- [ ] conflict resolution 규칙이 있는가?
- [ ] evaluation dataset이 있는가?
- [ ] trace/observability가 있는가?

### 13.2 Prompt/Context 리뷰 체크리스트

- [ ] 현재 목표가 분명히 들어가 있는가?
- [ ] 모델이 보면 안 되는 정보가 들어가 있지 않은가?
- [ ] 오래된 정보와 최신 정보가 구분되는가?
- [ ] 출처가 유지되는가?
- [ ] 도구 설명이 중복되거나 모호하지 않은가?
- [ ] 출력 형식이 검증 가능한가?
- [ ] “모르면 모른다” fallback이 있는가?
- [ ] 사람이 승인해야 하는 행동이 분리되어 있는가?

### 13.3 평가 체크리스트

- [ ] context precision: 넣은 context가 실제로 관련 있는가?
- [ ] context recall: 필요한 context를 빠뜨리지 않았는가?
- [ ] faithfulness: 답변이 context에 근거하는가?
- [ ] answer relevance: 사용자 질문에 답하는가?
- [ ] tool accuracy: 올바른 도구를 골랐는가?
- [ ] memory accuracy: 올바른 기억을 골랐는가?
- [ ] cost/latency: 허용 범위인가?
- [ ] safety: 민감 정보/side effect 처리가 안전한가?

---

## 14. 실무 템플릿

## 14.1 Context Policy 템플릿

```yaml
context_policy:
  use_case: ""
  owner: ""
  model: ""
  token_budget:
    max_input_tokens: 0
    reserved_output_tokens: 0
  always_include:
    - ""
  include_when_relevant:
    - name: ""
      source: ""
      retrieval_method: ""
      max_tokens: 0
  never_include:
    - ""
  retrieval:
    query_rewrite: true
    hybrid_search: true
    rerank: true
    top_k: 20
    final_k: 5
    metadata_filters:
      - ""
  memory:
    read_strategy: "relevance_recency_permission"
    max_items: 5
    write_allowed:
      - "explicit user preferences"
      - "stable project decisions"
    write_denied:
      - "secrets"
      - "unverified assumptions"
  tools:
    selection_strategy: "intent_allowlist"
    require_approval_for:
      - "external_send"
      - "delete"
      - "payment"
  compression:
    trigger_tokens: 60000
    preserve:
      - "decisions"
      - "sources"
      - "open_tasks"
  conflict_resolution:
    priority:
      - "latest official source"
      - "explicit user instruction"
      - "verified tool result"
  observability:
    log_retrieval: true
    log_tool_calls: true
    redact_pii: true
```

## 14.2 Context Pack 템플릿

```markdown
# Context Pack

## Role
...

## Objective
...

## Success Criteria
- ...

## Constraints
- ...

## Current State
```json
{}
```

## Relevant Memory
- [memory_id] ...

## Retrieved Knowledge
### Source 1
- source_id:
- date:
- reliability:
- excerpt:

## Available Tools
- tool_name: purpose, constraints

## Output Contract
```json
{}
```

## User Request
...
```

## 14.3 Retrieval Result 템플릿

```json
{
  "query": "",
  "rewritten_query": "",
  "results": [
    {
      "source_id": "",
      "title": "",
      "url": "",
      "date": "",
      "score": 0.0,
      "excerpt": "",
      "why_selected": ""
    }
  ],
  "excluded": [
    {
      "source_id": "",
      "reason": "outdated / duplicate / low relevance / no permission"
    }
  ],
  "conflicts": []
}
```

## 14.4 Memory Record 템플릿

```json
{
  "id": "mem_001",
  "type": "semantic | episodic | procedural",
  "content": "",
  "source": "user_explicit | inferred | tool_verified",
  "created_at": "",
  "updated_at": "",
  "confidence": 0.0,
  "sensitivity": "low | medium | high",
  "expires_at": null,
  "tags": []
}
```

## 14.5 Tool Result Compaction 템플릿

```json
{
  "tool": "",
  "input_summary": "",
  "status": "success | failure",
  "key_results": [],
  "errors": [],
  "source_ids": [],
  "next_recommended_action": "",
  "raw_output_location": ""
}
```

---

## 15. 도입 로드맵

## 15.1 1주차: 현재 시스템 진단

- 주요 LLM use case 목록화
- 실패 사례 수집
- prompt/context/tool 로그 확인
- 현재 context inventory 작성
- 가장 비용이 큰/실패가 많은 use case 선정

산출물:

- `context-inventory.md`
- `failure-cases.md`
- baseline eval set

## 15.2 2주차: Retrieval/Memory/Tool 정책 수립

- always/include/never context 정의
- retrieval pipeline 설계
- memory policy 작성
- tool allowlist와 approval rule 정의
- output schema 도입

산출물:

- `context-policy.yaml`
- `tool-registry.yaml`
- `memory-policy.yaml`

## 15.3 3주차: 평가와 관측성 구축

- eval cases 작성
- trace logging 적용
- context precision/recall 측정
- 도구 호출 성공률 측정
- 비용/지연 baseline 측정

산출물:

- eval report
- observability dashboard

## 15.4 4주차: 압축/격리/최적화

- 긴 대화 요약 도입
- tool output compaction
- 하위 agent 또는 workflow 분리
- 비용 최적화
- 실패 케이스 재평가

산출물:

- compression policy
- multi-agent/workflow design
- before/after metrics

---

## 16. Best Practices

1. **작게 시작하라**
   - 모든 것을 agent로 만들지 말고, 단일 LLM call + retrieval부터 시작한다.

2. **컨텍스트 창을 소유하라**
   - 프레임워크가 알아서 넣는 prompt, tool, memory를 반드시 확인한다.

3. **항상 출처를 유지하라**
   - retrieved chunk, memory, tool result에 source/provenance를 붙인다.

4. **도구는 적게, 명확하게 제공하라**
   - 도구가 많을수록 confusion이 증가한다.

5. **요약은 검증 가능하게 하라**
   - 숫자, ID, URL, 결정사항은 원문 참조를 유지한다.

6. **메모리는 관련 있을 때만 불러오라**
   - 모든 사용자 기억을 항상 넣지 않는다.

7. **충돌을 숨기지 말라**
   - 문서 간 충돌이 있으면 모델에게 명시하고 해결 규칙을 제공한다.

8. **긴 컨텍스트보다 좋은 검색이 낫다**
   - 큰 context window는 안전망이지 설계 대체물이 아니다.

9. **workflow와 agent를 구분하라**
   - 예측 가능한 절차는 workflow로, 동적 판단이 필요한 곳만 agent로 둔다.

10. **평가 없이 개선하지 말라**
    - retrieval, memory, tool selection 각각을 측정한다.

---

## 17. 주요 출처

아래 자료들을 바탕으로 본 문서를 정리했다.

1. LangChain Blog, “Context Engineering for Agents”  
   https://www.langchain.com/blog/context-engineering-for-agents

2. LangChain GitHub, `langchain-ai/context_engineering`  
   https://github.com/langchain-ai/context_engineering

3. Mei et al., “A Survey of Context Engineering for Large Language Models”, arXiv:2507.13334  
   https://arxiv.org/abs/2507.13334

4. Weaviate Blog, “Context Engineering - LLM Memory and Retrieval for AI Agents”  
   https://weaviate.io/blog/context-engineering

5. Anthropic Engineering, “Building effective agents”  
   https://www.anthropic.com/engineering/building-effective-agents

6. Anthropic Engineering, “How we built our multi-agent research system”  
   https://www.anthropic.com/engineering/multi-agent-research-system

7. Drew Breunig, “How Long Contexts Fail”  
   https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html

8. Model Context Protocol Documentation, “What is the Model Context Protocol?”  
   https://modelcontextprotocol.io/introduction

9. HumanLayer, “12-Factor Agents” GitHub  
   https://github.com/humanlayer/12-factor-agents

10. HumanLayer Blog, “12 Factor Agents”  
    https://www.humanlayer.dev/blog/12-factor-agents

11. LlamaIndex GitHub  
    https://github.com/run-llama/llama_index

12. DSPy GitHub  
    https://github.com/stanfordnlp/dspy

13. Haystack GitHub  
    https://github.com/deepset-ai/haystack

14. Weaviate GitHub  
    https://github.com/weaviate/weaviate

15. Chroma GitHub  
    https://github.com/chroma-core/chroma

16. Qdrant GitHub  
    https://github.com/qdrant/qdrant

17. FAISS GitHub  
    https://github.com/facebookresearch/faiss

18. LanceDB GitHub  
    https://github.com/lancedb/lancedb

19. PydanticAI GitHub  
    https://github.com/pydantic/pydantic-ai

20. Instructor GitHub  
    https://github.com/instructor-ai/instructor

21. Microsoft Semantic Kernel GitHub  
    https://github.com/microsoft/semantic-kernel

22. Microsoft AutoGen GitHub  
    https://github.com/microsoft/autogen

23. CrewAI GitHub  
    https://github.com/crewAIInc/crewAI

24. Ragas GitHub  
    https://github.com/explodinggradients/ragas

25. DeepEval GitHub  
    https://github.com/confident-ai/deepeval

26. Langfuse GitHub  
    https://github.com/langfuse/langfuse

27. Arize Phoenix GitHub  
    https://github.com/Arize-ai/phoenix

---

## 18. 결론

Context Engineering은 LLM 애플리케이션이 데모 수준을 넘어 실제 운영 가능한 시스템이 되기 위한 핵심 discipline이다. 좋은 모델을 고르는 것만으로는 부족하다. 모델이 매 순간 어떤 정보를 보고, 어떤 정보를 무시하며, 어떤 도구를 어떤 권한으로 사용하고, 무엇을 기억하고, 무엇을 잊을지 설계해야 한다.

실무적으로는 다음 문장으로 요약할 수 있다.

> Prompt는 모델에게 하는 말이고, Context는 모델이 일하는 세계다. Context Engineering은 그 세계를 설계하는 일이다.

가장 중요한 시작점은 거창한 multi-agent 시스템이 아니라, 현재 LLM 호출에 들어가는 컨텍스트를 눈으로 확인하고, 불필요한 것을 줄이며, 필요한 것을 출처와 함께 안정적으로 넣는 것이다. 그 위에 retrieval, memory, compression, tool selection, workflow, evaluation을 단계적으로 쌓아가면 된다.
