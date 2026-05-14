# Agent Drift 관점의 Prompt/Context Bloat 문제와 해결 전략

작성일: 2026-05-14  
작성자: 모모 🫧

## 1. 문제 정의

에이전트에 기능, 도구, 정책, 메모리, 예외 처리, 사용자 선호, 과거 대화 요약이 계속 추가되면 LLM 호출 시 포함되는 프롬프트와 컨텍스트가 커진다. 이 현상은 단순한 비용 증가를 넘어 다음 문제를 만든다.

1. **Context window 초과**: 시스템 프롬프트, 도구 스키마, 대화 이력, 검색 결과가 누적되어 모델 한계를 넘는다.
2. **응답 품질 저하**: 관련 정보가 있어도 긴 문맥에서 제대로 사용하지 못하거나, 불필요한 정보가 판단을 흐린다.
3. **Tool overload**: 도구가 많아질수록 올바른 도구 선택과 인자 생성이 어려워진다.
4. **Instruction conflict**: 오래된 정책, 새 정책, 사용자 선호, 도구 설명이 서로 충돌한다.
5. **Agent drift**: 시간이 지나며 원래 의도, 역할, 의사결정 기준, 도구 사용 패턴이 점진적으로 달라진다.

이 문제는 “더 큰 context window를 쓰면 해결된다”가 아니라, **LLM에게 매 호출마다 무엇을, 왜, 어떤 우선순위로 보여줄지 설계하는 context engineering 문제**로 보는 편이 맞다.

---

## 2. 관련 개념 정리

### 2.1 Agent drift

Rath(2026)는 agent drift를 “extended interaction sequences에서 agent behavior, decision quality, inter-agent coherence가 점진적으로 저하되는 현상”으로 정의하고, 세 가지 형태로 나눈다.

- **Semantic drift**: 원래 사용자 의도나 시스템 목적에서 점진적으로 벗어남
- **Coordination drift**: 다중 에이전트 간 합의/조율 메커니즘 붕괴
- **Behavioral drift**: 원래 설계하지 않은 전략이나 행동 양식 출현

해당 논문은 drift를 측정하기 위해 Agent Stability Index(ASI)를 제안하며, response consistency, tool usage patterns, reasoning pathway stability, inter-agent agreement rates 등을 관찰 지표로 제시한다. 단, 이 문헌은 2026년 arXiv preprint이므로 production 적용 시 별도 검증이 필요하다.

### 2.2 Context bloat / context rot

Context bloat는 대화 이력, tool result, 에러 로그, 중간 추론, 검색 결과가 계속 누적되어 LLM 입력이 비대해지는 현상이다. Verma(2026)는 장기 소프트웨어 엔지니어링 에이전트에서 context bloat가 비용, 지연, reasoning degradation을 일으킨다고 설명한다.

LangChain은 에이전트의 context 실패 양상을 다음처럼 정리한다.

- **Context poisoning**: 환각이나 잘못된 정보가 context에 들어가 이후 판단을 오염
- **Context distraction**: 너무 많은 정보가 모델의 주의를 분산
- **Context confusion**: 불필요한 정보가 응답에 영향을 줌
- **Context clash**: context 내부 정보끼리 충돌

### 2.3 Lost in the Middle

Liu et al.(2023)은 긴 입력에서 관련 정보 위치가 앞/뒤에 있을 때보다 중간에 있을 때 성능이 크게 떨어지는 “Lost in the Middle” 현상을 보였다. 즉, context window 안에 정보가 있다고 해서 모델이 안정적으로 활용하는 것은 아니다.

이 결과는 에이전트 설계에서 중요하다. 기능 추가로 프롬프트가 길어지면 중요한 정책이나 목표가 “중간”에 묻혀 실제 행동에 반영되지 않을 수 있다.

### 2.4 Tool-use robustness 문제

WildToolBench는 실제 사용자 행동 기반의 multi-turn, multi-step tool-use를 평가하면서 compositional tasks, implicit intent, instruction transition이 tool-use를 어렵게 만든다고 보고했다. 57개 LLM 평가에서 어떤 모델도 15%를 넘지 못했다고 요약한다.

τ-bench도 도메인 API와 정책 문서가 있는 현실적 대화 환경에서 state-of-the-art function calling agents조차 성공률이 50% 미만이고 일관성이 낮다고 보고한다.

따라서 기능이 늘어날수록 단순히 “도구를 더 많이 제공”하는 방식은 품질을 보장하지 않는다.

---

## 3. 원인 분석: 기능 추가가 왜 drift를 만든다

| 원인 | 발생 방식 | 결과 |
|---|---|---|
| 프롬프트 누적 | 기능마다 지침, 예외, 예시, 정책 추가 | 핵심 목표가 희석됨 |
| 도구 스키마 증가 | 모든 도구 설명을 매번 노출 | 도구 선택 오류, 토큰 증가 |
| 대화 이력 누적 | 오래된 실패, 중간 결과, 잡담이 남음 | context distraction/poisoning |
| 메모리 무분별 삽입 | 관련 없는 장기 기억까지 주입 | 사용자 의도 왜곡, privacy risk |
| 정책 충돌 | 새 규칙과 오래된 규칙이 동시에 존재 | 불안정한 응답, 예측 불가 행동 |
| 다중 에이전트 조율 실패 | 각 agent가 서로 다른 context와 목표를 가짐 | coordination drift |
| 평가 부재 | 기능 추가 후 regression 측정 없음 | drift가 누적되어 늦게 발견 |

핵심은 **에이전트의 capability set은 커지는데, LLM 호출은 여전히 제한된 working memory 안에서 단일 판단을 해야 한다**는 점이다.

---

## 4. 해결 전략

### 전략 1. Context Engineering을 제품 아키텍처의 핵심 계층으로 둔다

LangChain은 context engineering을 “각 단계에서 context window에 딱 필요한 정보를 채우는 기술”로 보고, 전략을 **write, select, compress, isolate** 네 가지로 분류한다.

적용 방법:

1. **Write**: 모든 것을 prompt에 넣지 말고 외부 state, scratchpad, memory store, DB, 파일에 기록한다.
2. **Select**: 현재 task에 필요한 정보만 retrieval/routing으로 선택해 넣는다.
3. **Compress**: 오래된 대화와 tool result를 요약/압축한다.
4. **Isolate**: 서로 다른 기능, 도구, 작업 단계를 별도 agent/context로 분리한다.

권장 설계:

```text
User request
  -> intent/router
  -> task-specific prompt pack
  -> relevant memory retrieval
  -> dynamic tool subset
  -> bounded working context
  -> output/eval/logging
```

즉, 하나의 거대한 system prompt가 아니라 **상황별로 조립되는 prompt packet** 구조가 필요하다.

---

### 전략 2. 기능별 Prompt Pack / Capability Module로 분리한다

기능이 추가될 때마다 global system prompt에 붙이면 prompt bloat가 빠르게 악화된다. 대신 기능을 모듈화한다.

권장 구조:

```text
core_policy.md          # 항상 필요한 최소 정책
persona.md              # 톤/정체성, 가능하면 짧게
router_prompt.md         # 요청 분류용
capabilities/
  calendar.md            # 캘린더 작업 시에만 로드
  email.md               # 이메일 작업 시에만 로드
  coding.md              # 코딩 작업 시에만 로드
  research.md            # 리서치 작업 시에만 로드
  browser.md             # 브라우저 자동화 시에만 로드
```

원칙:

- 모든 기능 설명을 항상 넣지 않는다.
- router가 기능을 고른 뒤 해당 기능의 prompt pack만 로드한다.
- 기능 pack은 목적, 입력, 출력 형식, 도구 사용 규칙, 실패 처리만 포함한다.
- 기능 pack마다 token budget을 둔다.

장점:

- 새 기능 추가가 global prompt 품질을 망치지 않는다.
- 기능별 regression test가 쉬워진다.
- instruction conflict를 줄인다.

---

### 전략 3. Dynamic Tool Selection / Tool Retrieval을 사용한다

도구가 많아질수록 모든 tool schema를 한 번에 주는 방식은 위험하다. 도구도 문서처럼 retrieval/routing 대상이 되어야 한다.

권장 패턴:

1. **Tool registry**: 각 도구에 name, description, input schema, examples, tags, risk level, required permission 저장
2. **Tool router**: 사용자 요청을 분석해 후보 도구 3~8개만 선택
3. **Tool clarification**: 후보가 애매하면 바로 실행하지 말고 짧게 확인
4. **Tool linting**: schema가 비슷한 도구는 이름/설명/인자를 명확히 분리
5. **Risk gating**: 외부 전송, 결제, 삭제, 공개 게시 등은 별도 승인 흐름

Tool-use benchmark들이 보여주는 것은 “LLM이 도구를 쓸 수 있다”와 “현실적인 multi-turn 상황에서 안정적으로 올바른 도구를 쓴다”는 완전히 다르다는 점이다. 따라서 도구 수를 늘리는 것보다 **도구 노출을 제한하고 선택 과정을 구조화**하는 것이 중요하다.

---

### 전략 4. 장기 기억과 작업 기억을 분리한다

MemGPT는 제한된 context window 문제를 OS의 hierarchical memory에 비유하며, fast memory와 slow memory 사이의 data movement로 virtual context management를 제안한다. Generative Agents도 경험 전체를 자연어 memory에 저장하되, planning에 필요한 기억을 동적으로 검색하고 reflection으로 고수준 기억을 생성한다.

권장 메모리 계층:

| 계층 | 용도 | context 삽입 방식 |
|---|---|---|
| System/Core | 안전, 역할, 불변 정책 | 항상 포함, 매우 짧게 |
| Working memory | 현재 task state, plan, TODO | 현재 task에만 포함 |
| Episodic memory | 과거 상호작용/시도/실패 | 관련도 기반 검색 |
| Semantic memory | 사용자 선호, 도메인 사실 | 관련도 + 최신성 기반 검색 |
| Procedural memory | 작업 방법, tool 사용법 | 기능 pack에서 선택 로드 |
| Archive/log | 원본 대화, tool logs | 필요 시 조회, 기본 미포함 |

주의점:

- memory는 “많을수록 좋은 것”이 아니다.
- 기억을 삽입하기 전에 relevance, recency, authority, sensitivity를 평가해야 한다.
- 오래된 memory는 decay/expire/review 정책을 둔다.
- 사용자 선호와 시스템 정책이 충돌하면 우선순위를 명시한다.

---

### 전략 5. Active Context Compression을 도입한다

Verma(2026)의 Focus는 에이전트가 스스로 중요한 학습 내용을 Knowledge block에 통합하고 raw interaction history를 prune하는 방식으로 SWE-bench Lite 일부 작업에서 정확도는 유지하면서 토큰을 22.7% 줄였다고 보고한다. 표본 수가 N=5로 작기 때문에 일반화에는 주의가 필요하지만, 방향성은 실무적으로 유용하다.

권장 compression trigger:

- context 사용량이 60~70%를 넘을 때
- tool result가 10개 이상 누적될 때
- 같은 에러가 반복될 때
- task phase가 바뀔 때: 조사 → 구현, 구현 → 검증 등
- 사용자 의도가 확정되었을 때

압축 결과 형식 예시:

```markdown
## Task State Summary
- Goal:
- Constraints:
- Decisions made:
- Important facts with sources:
- Failed attempts and why:
- Open questions:
- Next action:
```

중요한 점은 요약이 또 다른 hallucination source가 될 수 있다는 것이다. 따라서 압축에는 다음 안전장치가 필요하다.

- 원본 log reference/id 유지
- 사실과 추론 분리
- 불확실한 항목 표시
- 최신 요약이 이전 요약을 어떻게 대체하는지 명시

---

### 전략 6. RAG는 “적게, 정확히” 넣는 방향으로 설계한다

Anthropic의 Contextual Retrieval은 chunk만 embedding하면 맥락이 사라져 retrieval 실패가 발생할 수 있다고 지적한다. chunk마다 문서 내 위치/의미를 설명하는 짧은 context를 붙여 embedding/BM25 index를 만들면 retrieval 실패를 줄일 수 있다고 보고한다. Anthropic은 contextual embeddings와 contextual BM25로 failed retrieval을 49%, reranking 결합 시 67% 줄였다고 설명한다.

적용 방법:

- 단순 vector search만 쓰지 말고 BM25 + embedding + reranking 조합 사용
- chunk에 문서명, 섹션, 날짜, 엔티티, 버전 정보를 붙임
- top-K를 크게 잡지 말고 reranker로 줄임
- 검색 결과는 “근거 묶음”으로 구조화해서 삽입
- 오래된 문서와 최신 문서가 충돌하면 freshness/authority 기준으로 정렬

RAG의 목적은 context를 많이 넣는 것이 아니라, **결정에 필요한 근거만 정확히 넣는 것**이다.

---

### 전략 7. Orchestrator-worker / Multi-agent isolation을 제한적으로 사용한다

Anthropic은 multi-agent research system에서 subagent들이 독립 context window로 여러 방향을 병렬 탐색하고, lead agent가 결과를 압축/종합하는 구조가 연구 작업에 효과적이었다고 설명한다. 내부 평가에서는 multi-agent system이 single-agent보다 90.2% 우수했지만, multi-agent는 일반 chat 대비 약 15배 토큰을 사용한다고도 밝힌다.

적합한 경우:

- 연구/조사처럼 탐색 방향이 여러 개인 작업
- 정보량이 단일 context window를 초과하는 작업
- 독립 하위 작업으로 분리 가능한 작업

부적합한 경우:

- 모든 agent가 동일한 상태를 공유해야 하는 작업
- 의존성이 강한 순차 작업
- 비용/지연이 매우 민감한 작업
- 조율 자체가 더 어려운 작업

실무 권장:

- “모든 기능을 한 agent에 넣기”보다 “router + specialist agents”가 낫다.
- 단, specialist가 너무 많으면 coordination drift가 생긴다.
- subagent output은 반드시 짧은 structured report로 제한한다.

---

### 전략 8. Drift Metrics와 Regression Evaluation을 운영한다

기능 추가가 응답 품질을 망치는 문제는 대부분 “느리게 누적”된다. 따라서 drift를 측정해야 한다.

권장 지표:

| 범주 | 지표 |
|---|---|
| Context | 입력 토큰 수, tool schema 토큰 수, memory 삽입 토큰 수, compression 횟수 |
| 품질 | golden task accuracy, human rating, citation accuracy, instruction following |
| 안정성 | 동일 요청 반복 시 일관성, pass^k, variance |
| 도구 | tool selection accuracy, invalid tool call rate, retry rate, permission violation near-miss |
| Drift | persona/policy consistency, reasoning pathway stability, tool usage pattern shift |
| 비용 | latency, total tokens, tool calls per task, dollars per success |

권장 평가 세트:

1. **Core behavior eval**: 정체성, 안전 정책, 응답 형식이 변하지 않는지
2. **Feature-specific eval**: 새 기능이 자기 영역에서 잘 작동하는지
3. **Cross-feature interference eval**: 기능 A 추가가 기능 B를 망치지 않는지
4. **Long-horizon eval**: 20~100턴 대화 후에도 목표를 유지하는지
5. **Tool overload eval**: 도구 수를 늘려도 선택 정확도가 유지되는지
6. **Memory pollution eval**: 잘못된 과거 정보가 들어갔을 때 회복하는지

CI에 넣을 최소 gate:

```text
prompt change PR
  -> token budget diff
  -> golden eval
  -> tool selection eval
  -> long-context regression sample
  -> drift score report
```

---

## 5. 권장 아키텍처

### 5.1 High-level 구조

```text
                      ┌────────────────────┐
User request ───────▶ │ Intent / Risk Router│
                      └─────────┬──────────┘
                                │
                ┌───────────────┼────────────────┐
                │               │                │
        Capability Pack   Memory Selector   Tool Selector
                │               │                │
                └───────────────┼────────────────┘
                                ▼
                      ┌────────────────────┐
                      │ Context Builder     │
                      │ - budget allocator  │
                      │ - conflict resolver │
                      │ - source ordering   │
                      └─────────┬──────────┘
                                ▼
                      ┌────────────────────┐
                      │ Bounded Agent Call  │
                      └─────────┬──────────┘
                                ▼
                      ┌────────────────────┐
                      │ Eval / Guard / Log  │
                      └─────────┬──────────┘
                                ▼
                      Response / Tool Action
```

### 5.2 Context budget 예시

| 항목 | 권장 비율 | 설명 |
|---|---:|---|
| Core policy | 5~10% | 짧고 불변인 핵심 규칙 |
| Task instruction | 10~20% | 현재 요청에 필요한 기능 pack |
| Working state | 10~20% | 현재 계획, 진행 상태 |
| Retrieved memory/knowledge | 20~35% | 관련 근거만 |
| Tool schemas | 10~20% | 선택된 후보 도구만 |
| Output reserve | 15~25% | 답변/추론/도구 인자 생성을 위한 여유 |

절대 규칙:

- context window를 꽉 채우지 않는다.
- 중요한 instruction은 앞쪽 또는 마지막 reminder에 배치한다.
- 중간에 묻히는 핵심 정책을 만들지 않는다.
- 도구 결과 원문을 계속 누적하지 않는다.

---

## 6. 기능 추가 프로세스 제안

새 기능을 추가할 때 다음 체크리스트를 통과하도록 한다.

### 6.1 설계 체크리스트

- [ ] 이 기능은 global prompt에 들어가야 하는가, capability pack으로 충분한가?
- [ ] 항상 필요한 도구인가, task-specific tool인가?
- [ ] 이 기능이 기존 정책/도구/메모리와 충돌하는가?
- [ ] 이 기능의 prompt token budget은 얼마인가?
- [ ] 실패 시 fallback/clarification 정책이 있는가?
- [ ] regression eval이 있는가?

### 6.2 배포 체크리스트

- [ ] prompt/token diff 확인
- [ ] golden eval 통과
- [ ] tool selection eval 통과
- [ ] long-context scenario 통과
- [ ] drift metric 악화 여부 확인
- [ ] 실제 로그에서 불필요한 context 삽입률 확인

---

## 7. 우선순위별 실행 로드맵

### Phase 1. 즉시 적용 가능한 개선

1. global prompt에서 기능별 지침을 분리한다.
2. tool schema를 전부 넣지 말고 task별 후보만 넣는다.
3. 대화 이력은 최근 N턴 + 요약으로 제한한다.
4. tool result는 raw log 대신 결과 요약만 유지한다.
5. token budget report를 매 요청마다 기록한다.

### Phase 2. 구조적 개선

1. intent router + capability pack loader 구현
2. memory selector 구현: relevance/recency/authority/sensitivity scoring
3. compression trigger와 task-state summary 구현
4. BM25 + embedding + reranking 기반 knowledge retrieval 구축
5. prompt/module별 regression eval 구축

### Phase 3. Drift-aware 운영

1. Agent Stability Index 유사 지표 도입
2. 기능 추가 PR마다 drift report 생성
3. long-horizon simulation eval 운영
4. policy conflict detector 구축
5. multi-agent isolation은 고가치 병렬 작업에만 제한 적용

---

## 8. 결론

에이전트 기능 추가로 인한 prompt/context bloat는 토큰 한도 문제가 아니라 **에이전트 안정성 문제**다. context가 길어질수록 모델은 중요한 정보를 놓치고, 불필요한 정보에 흔들리며, 도구 선택과 정책 준수도 불안정해진다. 이 현상은 agent drift의 주요 원인 중 하나다.

가장 현실적인 해법은 다음 조합이다.

1. **Global prompt 최소화**
2. **기능별 capability pack 동적 로딩**
3. **tool retrieval / dynamic tool subset**
4. **working memory와 long-term memory 분리**
5. **active context compression**
6. **정확한 RAG와 reranking**
7. **orchestrator-worker isolation의 제한적 사용**
8. **drift metric + regression eval 운영**

즉, 에이전트 확장성은 “기능을 얼마나 많이 붙일 수 있느냐”가 아니라, **매 순간 LLM에게 필요한 최소 충분 context를 구성하는 능력**에 달려 있다.

---

## 9. 출처

1. Abhishek Rath, **“Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over Extended Interactions”**, arXiv:2601.04170, 2026.  
   https://arxiv.org/abs/2601.04170

2. Nikhil Verma, **“Active Context Compression: Autonomous Memory Management in LLM Agents”**, arXiv:2601.07190, 2026.  
   https://arxiv.org/abs/2601.07190

3. Nelson F. Liu et al., **“Lost in the Middle: How Language Models Use Long Contexts”**, TACL / arXiv:2307.03172, 2023.  
   https://arxiv.org/abs/2307.03172

4. LangChain, **“Context Engineering for Agents”**, 2025.  
   https://www.langchain.com/blog/context-engineering-for-agents

5. Anthropic, **“How we built our multi-agent research system”**, 2025.  
   https://www.anthropic.com/engineering/multi-agent-research-system

6. Anthropic, **“Introducing Contextual Retrieval”**, 2024.  
   https://www.anthropic.com/engineering/contextual-retrieval

7. Anthropic, **“Building effective agents”**, 2024.  
   https://www.anthropic.com/engineering/building-effective-agents

8. Noah Shinn et al., **“Reflexion: Language Agents with Verbal Reinforcement Learning”**, arXiv:2303.11366, 2023.  
   https://arxiv.org/abs/2303.11366

9. Joon Sung Park et al., **“Generative Agents: Interactive Simulacra of Human Behavior”**, arXiv:2304.03442, 2023.  
   https://arxiv.org/abs/2304.03442

10. Charles Packer et al., **“MemGPT: Towards LLMs as Operating Systems”**, arXiv:2310.08560, 2023/2024.  
    https://arxiv.org/abs/2310.08560

11. **“Benchmarking LLM Tool-Use in the Wild”**, OpenReview / WildToolBench.  
    https://openreview.net/forum?id=yz7fL5vfpn

12. Karthik Narasimhan et al., **“τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains”**, arXiv:2406.12045, 2024.  
    https://arxiv.org/abs/2406.12045
