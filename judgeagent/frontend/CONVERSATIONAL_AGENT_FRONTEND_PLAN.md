# Conversational Judge Agent Frontend Development Plan

## 1. 목적

`simple/judge_agent_simple`의 대화형 Judge Agent와 `reference_agent/weblog_agent` reference target agent를 하나의 웹 UI에서 다룬다. 사용자는 Reference Agent를 실행해 trace/report를 생성하거나 기존 trace를 업로드/선택하고, Judge Agent로 분석한 뒤 채팅으로 drift 원인, 근거, 수정 우선순위, run 비교를 질의할 수 있어야 한다.

디자인 기준은 `frontend/DESIGN.md`를 따른다. 실제 Agent ↔ Frontend 연동을 위한 상세 API 계약과 구현 순서는 `frontend/API_INTEGRATION_PLAN.md`, endpoint별 request/response는 `frontend/API_REFERENCE.md`를 따른다.

핵심 방향:

- cream canvas 기반의 조용한 technical UI
- 얇은 hairline border 중심의 flat card layout
- shadow 없는 정보 밀도 높은 화면
- code/evidence 영역만 dark olive-charcoal surface 사용
- metric/finding/status는 pill chip, badge, callout banner로 표현
- 대화형 에이전트이지만 “챗봇 앱”보다 “reference run → trace → judge review”가 이어지는 drift review workspace처럼 설계
- Reference Agent의 ReAct loop, Tool/RAG/MCP/Validation trace를 Judge Agent 분석과 나란히 볼 수 있게 설계

## 2. 추천 기술 스택

현재 repo에는 frontend app skeleton이 없으므로 1차 구현은 다음 구성을 추천한다.

| Layer | Recommendation | Reason |
| --- | --- | --- |
| App | Vite + React + TypeScript | 빠른 MVP, repo에 가볍게 추가 가능 |
| Styling | CSS Modules 또는 plain CSS variables | `DESIGN.md` token을 그대로 CSS variable로 매핑하기 쉬움 |
| State | Zustand 또는 React reducer | session, selected run/finding, chat messages 관리가 단순함 |
| API | FastAPI backend 추가 | Python Judge Agent runtime을 직접 호출하기 좋음 |
| Streaming | SSE 우선, WebSocket은 Phase 2 | agent response streaming 확장 가능 |
| Test | Vitest + React Testing Library | 컴포넌트/상태 테스트 |
| E2E | Playwright | 업로드→분석→채팅 플로우 검증 |

초기에는 Vite가 가장 단순하다. Next.js는 routing/API를 한 번에 관리하기 좋지만, Python agent runtime과 붙을 예정이라 프론트는 정적 SPA + Python API 분리가 더 깔끔하다.

## 3. 제품 구조

```text
frontend/
  DESIGN.md
  CONVERSATIONAL_AGENT_FRONTEND_PLAN.md
  app/                         # Phase 1에서 생성 예정
    package.json
    index.html
    src/
      main.tsx
      App.tsx
      styles/
        tokens.css
        global.css
      components/
        AppShell.tsx
        PrimaryNav.tsx
        Sidebar.tsx
        ReferenceAgentPanel.tsx
        ReferenceRunTimeline.tsx
        ChatPanel.tsx
        FindingsPanel.tsx
        MetricCard.tsx
        EvidenceBlock.tsx
        TraceUploadCard.tsx
        RunCompareTable.tsx
      api/
        judgeClient.ts
      state/
        judgeStore.ts
      types/
        judge.ts
```

Python backend 후보:

```text
simple/judge_agent_simple/api.py          # FastAPI app
simple/judge_agent_simple/api_models.py   # Pydantic DTO
simple/judge_agent_simple/api_store.py    # file-backed registry, DB 교체 예정 지점
simple/judge_agent_simple/api_services.py # Reference/Judge orchestration
```

상세 endpoint, DTO, error contract, file-backed store 설계는 `frontend/API_INTEGRATION_PLAN.md`에 정의한다.

## 4. 핵심 사용자 시나리오

### 4.1 Trace 분석 시작

1. 사용자가 JSONL trace 파일을 업로드하거나 path/glob을 입력한다.
2. adapter, mode, LLM provider를 선택한다.
3. `Analyze traces` 버튼을 누른다.
4. backend가 `analyze_traces` 또는 conversation agent `load_analysis`를 실행한다.
5. UI는 run count, gate count, severity count, top findings를 보여준다.

### 4.2 대화형 분석

1. 사용자가 “왜 block이야?”, “JD-001 근거”, “수정 우선순위 알려줘”를 입력한다.
2. backend가 `ToolBasedConversationAgent`, `HybridConversationAgent`, 또는 `GraphConversationAgent`를 호출한다.
3. UI는 assistant response와 함께 사용된 tool, evidence, focused metric을 표시한다.
4. finding/focused metric이 바뀌면 우측 detail panel이 동기화된다.

### 4.3 Finding drilldown

1. 사용자가 finding card를 클릭한다.
2. 우측 detail panel에 expected/actual/evidence/recommendation이 열린다.
3. `Ask about this finding` CTA가 채팅 입력에 context chip을 추가한다.

### 4.4 Run 비교

1. 사용자가 `Compare runs` tab을 선택한다.
2. block/warning/pass, score, finding count 기준으로 정렬된 table을 보여준다.
3. run row 클릭 시 해당 run의 top findings를 보여준다.

### 4.5 Reference Agent 실행 및 Judge 분석

1. 사용자가 Reference Agent 화면에서 fixture를 선택한다. 예: `normal-login-error-spike`, validation skipped drift, metric hallucination drift.
2. LLM 사용 여부를 선택한다. 기본은 CI 재현성을 위해 `--no-llm` deterministic fallback이다.
3. `Run reference agent` 버튼을 누르면 backend가 `reference_agent.weblog_agent.cli`와 동일한 runtime을 호출한다.
4. UI는 생성된 report, JSONL trace, ReAct timeline, Tool/RAG/MCP/Validation 이벤트를 표시한다.
5. 사용자가 `Judge this trace`를 누르면 해당 trace가 Judge Agent 분석으로 전달된다.
6. Judge Agent 결과와 Reference Agent 실행 과정을 한 화면에서 연결해 본다.

### 4.6 Reference Agent Interactive Chat Review

1. 사용자가 reference chat session을 시작한다.
2. 첫 질문으로 웹로그 분석 요청을 입력한다.
3. Reference Agent가 child ReAct analysis trace와 chat trace를 생성한다.
4. 이후 “방금 결과에서 가장 의심되는 원인은?” 같은 follow-up을 입력한다.
5. Judge Agent는 reference chat trace의 `chat_context_built`, `chat_analysis_invoked`, `chat_response_generated` 이벤트를 분석해 chat grounding drift를 탐지한다.

## 5. 화면 설계

## 5.1 App Shell

`DESIGN.md`의 cream canvas와 primary-nav를 따른다.

```text
┌─────────────────────────────────────────────────────────────┐
│ Judge Agent · Drift Review             Search  Settings CTA │ 56px primary-nav
├─────────────────────────────────────────────────────────────┤
│ Sessions · Traces · Metrics · Config           New analysis │ 40px sub-nav-strip
├───────────────┬─────────────────────────────┬───────────────┤
│ Sidebar       │ Main Review Workspace        │ Detail Panel   │
│ Sessions      │ Summary / Chat / Findings    │ Evidence       │
│ Filters       │                             │ Recommendation│
└───────────────┴─────────────────────────────┴───────────────┘
```

디자인 규칙:

- body background: `{colors.canvas}` cream
- nav/subnav: radius none, shadow 없음
- panel/card: white/warm-white + 1px hairline
- section 분리는 decorative divider 대신 eyebrow + 1px hairline
- primary CTA는 한 화면에 하나만 yellow-orange

## 5.2 Dashboard / Review Home

구성:

- Hero summary card
  - “Review agent drift from trace evidence”
  - run count, block/warning/pass badges
  - primary CTA: `Analyze traces`
- 3-up metric tiles
  - Gate status
  - Severity distribution
  - Top priority finding
- Recent sessions list
- Config status callout
  - active mode, provider, model, config directory

디자인:

- `product-card`, `feature-tile` 패턴 사용
- severity는 pill chip으로 표시
- critical/high는 saturated background가 아니라 border/text emphasis 위주로 표현

## 5.3 Chat Workspace

주요 영역:

- left sidebar: sessions, loaded traces, filter chips
- center: chat transcript + input
- right detail: focused finding/evidence/tool calls

Chat message 디자인:

| Message | Treatment |
| --- | --- |
| user | cream canvas 위 flat bubble, hairline border |
| assistant | warm-white doc-card 느낌, evidence footnote 포함 |
| tool call | compact inline-code chip + expandable row |
| fallback notice | `banner-tip-purple` 또는 `banner-tip-blue` |
| warning/block | `banner-tip-red` callout, 단 과도한 alert color 금지 |

입력 영역:

- `text-input` style
- placeholder examples: `왜 block이야?`, `JD-001 근거`, `run 비교`
- context chips: selected run/finding/metric
- send button은 primary CTA 대신 secondary/tertiary를 기본으로 두고, 새 분석 시작 버튼만 primary 유지

## 5.4 Findings Panel

카드 목록:

```text
JD-001 validation_path_coverage        CRITICAL · LangGraph Flow
Expected: validate_findings node and validation_result events...
Actual: Validation path was missing or explicitly skipped.
[Evidence 3] [Ask] [Fix priority]
```

디자인:

- `product-card`보다 조밀한 `doc-card` 변형
- severity pill은 inverted chip보다 hairline badge 우선
- metric category는 `badge-uppercase`
- recommendation은 green callout이 아니라 normal body + icon 정도로 절제

## 5.5 Evidence / Trace Detail

증거는 `code-block`과 `inline-code`를 적극 사용한다.

- raw event snippet
- tool_start/tool_end pair
- validation_result
- final_output excerpt

디자인:

- evidence body card 안에 dark code block
- code block만 유일한 dark elevated surface
- JSON은 monospace, 13px 전후
- 긴 evidence는 collapsed accordion

## 5.6 Reference Agent Lab

Reference Agent는 Judge Agent의 분석 대상이므로 별도 lab 화면을 둔다.

주요 영역:

- fixture selector: 정상/드리프트 scenario 선택
- run options: `no_llm`, LLM provider/model, access log path, session id
- run status: queued/running/succeeded/failed
- generated artifacts: trace JSONL, markdown report, session JSON
- ReAct timeline: Thought/Action/Observation step list
- context panels: RAG runbook, MCP service context, validation result
- CTA: `Judge this trace`

디자인:

- 전체는 `doc-card` 기반 technical workspace
- ReAct timeline은 hairline row divider만 사용
- raw trace excerpt는 `code-block` dark surface 사용
- Tool/RAG/MCP/Validation 이벤트는 `badge-uppercase` + inline-code chip으로 표현
- 정상 fixture와 drift fixture를 색으로 과하게 나누지 않고 pill label과 copy로 구분

## 5.7 Config / Model Settings

파일 기반 config를 보여주고 편집 가능성은 Phase 2로 미룬다.

표시 항목:

- active config dir: `JUDGE_CONFIG_DIR` 또는 bundled `simple/config`
- app defaults: adapter, session_dir, chat_mode, fail_on
- LLM provider profile: provider, base_url, default_model
- metric registry count
- detector thresholds

디자인:

- settings는 doc-sidebar + doc-card 문서형 레이아웃
- 값은 inline-code chip으로 표시
- API key는 절대 노출하지 않고 configured/not configured만 표시

## 6. 디자인 토큰 매핑 초안

`frontend/app/src/styles/tokens.css` 후보:

```css
:root {
  --color-canvas: #eeefe9;
  --color-surface-card: #ffffff;
  --color-surface-doc: #fcfcfa;
  --color-surface-soft: #e5e7e0;
  --color-surface-dark: #252820;
  --color-ink: #252820;
  --color-body: #4f5348;
  --color-mute: #74786d;
  --color-hairline: #c9cbbb;
  --color-hairline-soft: #dedfd6;
  --color-primary: #f5b53f;
  --color-primary-pressed: #e4a332;
  --color-on-primary: #252820;
  --radius-xs: 2px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-full: 9999px;
  --space-section: 80px;
}
```

주의:

- 실제 color token 값은 `DESIGN.md`에서 명시된 값만 확정하고, 누락 값은 구현 시 한 번 더 추출/보정한다.
- shadow token은 만들지 않는다.

## 7. Backend API 계획

CLI만으로는 프론트와 연동하기 어렵기 때문에 FastAPI backend를 추가한다. 이 섹션은 요약이며, 실제 구현 기준은 `frontend/API_INTEGRATION_PLAN.md`다.

### 7.1 Endpoint 초안

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | backend 상태 확인 |
| GET | `/api/config` | app/config/llm profile/metric count 조회 |
| GET | `/api/reference/fixtures` | Reference Agent fixture/scenario 목록 |
| POST | `/api/reference/runs` | Reference Agent run 또는 chat turn 실행 |
| GET | `/api/reference/runs` | Reference Agent run 목록 |
| GET | `/api/reference/runs/{id}` | Reference Agent run metadata/report 조회 |
| GET | `/api/reference/runs/{id}/trace` | 생성된 JSONL trace 조회 |
| POST | `/api/analyses` | trace path, uploaded trace, 또는 reference run trace 분석 |
| POST | `/api/judge/sessions` | conversation session 생성 |
| GET | `/api/judge/sessions` | session 목록 |
| GET | `/api/judge/sessions/{id}` | session state 조회 |
| POST | `/api/judge/sessions/{id}/messages` | user turn 처리 후 assistant response 반환 |
| GET | `/api/judge/sessions/{id}/stream` | Phase 2 streaming response |
| GET | `/api/metrics` | metric registry 조회 |
| GET | `/api/findings/{id}` | finding detail 조회 |

### 7.2 DTO 초안

```ts
type Gate = 'pass' | 'warning' | 'block';
type Severity = 'low' | 'medium' | 'high' | 'critical';

type AnalysisSummary = {
  sessionId: string;
  runCount: number;
  gateCounts: Record<Gate, number>;
  severityCounts: Record<Severity, number>;
  topFindings: Finding[];
};

type ReferenceRun = {
  id: string;
  fixture?: string;
  mode: 'fixture' | 'custom-analysis' | 'chat';
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  tracePath?: string;
  reportPath?: string;
  eventCounts: Record<string, number>;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  createdAt: string;
  toolCalls?: ToolCall[];
  focusedFindingId?: string;
  focusedMetric?: string;
};
```

## 8. 구현 Phase

## Phase 0 — Product/UI Spec 정리

목표: 구현 전 화면/데이터 계약을 고정한다.

작업:

- [ ] `DESIGN.md` token을 CSS variable 후보로 정리
- [ ] 주요 화면 wireframe 확정
- [ ] API DTO 초안 확정
- [ ] Judge Agent CLI runtime과 API runtime 재사용 경계 정의
- [ ] Reference Agent run/chat runtime을 API에서 호출하는 경계 정의

산출물:

- `frontend/CONVERSATIONAL_AGENT_FRONTEND_PLAN.md`
- `frontend/app/src/styles/tokens.css` 초안
- API contract 문서 또는 OpenAPI skeleton

## Phase 1 — Frontend Skeleton

목표: mock data 기반으로 화면을 먼저 만든다.

작업:

- [ ] Vite React TypeScript app 생성
- [ ] global layout / nav / sub-nav 구현
- [ ] design token CSS 적용
- [ ] Dashboard page 구현
- [ ] Chat workspace shell 구현
- [ ] Reference Agent Lab shell 구현
- [ ] mock reference runs/findings/session data 연결
- [ ] responsive 3-column → single-column collapse 구현

검증:

- [ ] `npm run build`
- [ ] component smoke tests
- [ ] screenshot 확인

## Phase 2 — Python API Backend

목표: 프론트가 실제 Judge Agent runtime과 통신한다.

작업:

- [ ] `simple/judge_agent_simple/api.py` FastAPI 추가
- [ ] `api_models.py`, `api_store.py`, `api_services.py` 추가
- [ ] `/api/health`, `/api/config`, `/api/metrics` 구현
- [ ] `/api/reference/fixtures`, `/api/reference/runs` 구현
- [ ] `/api/analyses` 구현
- [ ] `/api/judge/sessions`, `/api/judge/sessions/{id}/messages` 구현
- [ ] CORS/local dev 설정
- [ ] error response 표준화

검증:

- [ ] Python unit tests
- [ ] curl/API smoke tests
- [ ] frontend에서 실제 analyze 호출 성공

## Phase 3 — Reference Agent Integration

목표: Reference Agent를 UI에서 실행하고 생성 trace를 Judge Agent 분석으로 넘긴다.

작업:

- [ ] fixture 목록 조회/선택 UI 연결
- [ ] reference run 실행 API 연결
- [ ] generated trace/report artifact 표시
- [ ] ReAct timeline 렌더링
- [ ] Tool/RAG/MCP/Validation event detail 표시
- [ ] `Judge this trace` 버튼으로 analyze flow 연결

검증:

- [ ] `run-all --no-llm`에 해당하는 reference fixture 실행 가능
- [ ] 생성 trace가 Judge Agent 분석으로 연결됨
- [ ] validation skipped / metric hallucination drift fixture가 UI에서 식별됨

## Phase 4 — Conversation Integration

목표: 대화형 agent를 UI에서 실제로 사용한다.

작업:

- [ ] deterministic-v2 mode 연결
- [ ] hybrid mode/provider/model 선택 연결
- [ ] chat message 전송/응답 렌더링
- [ ] focused finding/metric 동기화
- [ ] tool call/evidence accordion 표시
- [ ] fallback/LLM unavailable banner 처리

검증:

- [ ] “왜 block이야?” 응답 확인
- [ ] “JD-001 근거” evidence 표시 확인
- [ ] “run 비교” table 표시 확인

## Phase 5 — Trace Upload & Session Persistence

목표: 실제 사용 가능한 review workflow 완성.

작업:

- [ ] JSONL upload 지원
- [ ] path/glob 입력 지원
- [ ] session 목록/재개 지원
- [ ] recent sessions sidebar
- [ ] loaded traces display
- [ ] local storage fallback 또는 backend session persistence

검증:

- [ ] 업로드→분석→채팅 full flow
- [ ] 브라우저 reload 후 session 복구

## Phase 6 — Polish & Technical Seminar Demo

목표: 세미나/데모용 완성도 확보.

작업:

- [ ] empty/loading/error states
- [ ] sample trace quick-start button
- [ ] responsive QA
- [ ] accessibility check
- [ ] Playwright E2E
- [ ] demo script 작성

검증:

- [ ] `npm run build`
- [ ] `npm run test`
- [ ] `python3 -m unittest discover -s simple/judge_agent_simple/tests`
- [ ] Playwright smoke test

## 9. MVP Scope

MVP에 포함:

- Reference Agent fixture 실행 및 generated trace/report 확인
- trace path/glob 입력
- analyze 실행
- summary/gate/severity/top findings 표시
- deterministic-v2 chat
- finding detail/evidence/recommendation panel
- config read-only view
- `DESIGN.md` 기반 cream/hairline/card UI

MVP에서 제외:

- 사용자 인증
- multi-user collaboration
- DB persistence
- config 웹 편집
- full streaming response
- full LangGraph visualization beyond Reference Agent timeline
- production deployment pipeline

## 10. 향후 DB 연동 고려

`simple/config/database_tables.md`의 table candidates와 맞춰 frontend data model을 설계한다.

DB화 우선순위:

1. reference agent runs / generated artifacts / trace event index
2. sessions / messages / tool calls / evidence
3. metric specs
4. detector rule sets / thresholds
5. LLM provider profiles
6. user/team/workspace settings

Frontend는 처음부터 API DTO를 통해서만 데이터를 받도록 하고, config JSON 파일을 직접 import하지 않는다. 이렇게 하면 JSON file-backed API에서 DB-backed API로 전환해도 UI 변경이 최소화된다.

## 11. 리스크와 대응

| Risk | 대응 |
| --- | --- |
| CLI 중심 runtime이라 request/response API 경계가 애매함 | FastAPI wrapper에서 Judge Agent session state와 Reference Agent run artifact를 명시적으로 관리 |
| LLM response 시간이 길어질 수 있음 | Phase 1은 non-streaming, Phase 2 이후 SSE 추가 |
| evidence JSON이 길어 UI가 복잡해짐 | accordion + dark code block + excerpt 우선 |
| DESIGN.md token 일부 값이 미정 | CSS variable 초안 작성 후 실제 화면에서 보정 |
| config/DB 전환 가능성 | frontend는 API DTO만 의존 |

## 12. 권장 다음 작업

1. `frontend/app` Vite React TypeScript skeleton 생성
2. `tokens.css` / `global.css` 작성
3. mock data로 Dashboard + Reference Agent Lab + Chat Workspace 구현
4. `frontend/API_INTEGRATION_PLAN.md` 기준으로 FastAPI skeleton 작성
5. Reference Agent run API → Judge analyses API → judge session/message API 순서로 연결

추천 시작 명령:

```bash
cd frontend
npm create vite@latest app -- --template react-ts
cd app
npm install
npm run dev
```

그 다음 `DESIGN.md` 기반 CSS token과 layout component부터 구현한다.
