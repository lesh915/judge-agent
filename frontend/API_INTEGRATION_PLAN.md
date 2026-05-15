# Judge Agent ↔ Frontend API Integration Plan

## 1. 목적

현재 `frontend/app`은 mock 데이터로 Reference Agent Lab, Judge Findings, Chat Workspace를 보여준다. 실제 제품이 되려면 다음 세 런타임을 API로 연결해야 한다.

1. **Reference Agent runtime** — `reference_agent/weblog_agent` 실행, trace/report/session artifact 생성
2. **Judge Agent analysis runtime** — `simple/judge_agent_simple` 분석, finding/gate/score 생성
3. **Conversational Judge runtime** — 분석 결과를 session에 올리고 follow-up 질문 처리

이 문서는 프론트와 에이전트가 서로 안정적으로 연동되도록 API boundary, DTO, 상태 저장, 단계별 구현 계획을 정의한다. Endpoint별 request/response 세부 형식은 `frontend/API_REFERENCE.md`를 기준으로 한다.

## 2. 핵심 원칙

- Frontend는 Python 내부 파일/JSON config를 직접 읽지 않는다. 항상 API DTO만 사용한다.
- API는 CLI를 shell subprocess로 감싸는 방식이 아니라, 가능한 한 Python 함수/runtime을 직접 import해서 호출한다.
- 긴 실행은 `queued/running/succeeded/failed` 상태를 갖는 run resource로 표현한다.
- 파일 기반 artifact는 1차 MVP에서 유지하되, API response에는 DB 전환 가능한 id/path/metadata 구조로 노출한다.
- API key나 secret 값은 절대 response에 포함하지 않는다. `configured: true/false`만 노출한다.
- Reference Agent trace와 Judge Agent finding을 연결하는 canonical key는 `trace_path`와 `run_id`다.

## 3. 권장 Backend 위치

```text
simple/judge_agent_simple/api.py          # FastAPI app entrypoint
simple/judge_agent_simple/api_models.py   # Pydantic DTO
simple/judge_agent_simple/api_store.py    # file-backed run/session registry
simple/judge_agent_simple/api_services.py # Reference/Judge orchestration service
```

왜 `simple/judge_agent_simple` 아래에 두는가:

- Judge Agent runtime과 config loader를 바로 재사용할 수 있다.
- `pyproject.toml`의 optional dependency `api = [fastapi, uvicorn]`와 자연스럽게 연결된다.
- 나중에 DB store로 바꿀 때 API service boundary만 유지하면 된다.

실행 명령 후보:

```bash
pip install -e '.[api]'
uvicorn simple.judge_agent_simple.api:app --reload --port 8787
```

Frontend `.env` 후보:

```bash
VITE_JUDGE_API_BASE_URL=http://localhost:8787
```

## 4. 전체 연동 흐름

```text
Frontend
  │
  ├─ GET /api/config
  ├─ GET /api/reference/fixtures
  │
  ├─ POST /api/reference/runs
  │    └─ Reference Agent executes fixture/custom/chat turn
  │       ├─ trace_path
  │       ├─ report_path
  │       └─ event summary
  │
  ├─ POST /api/analyses
  │    └─ Judge Agent analyzes trace_path(s)
  │       ├─ analysis_id
  │       ├─ summary
  │       └─ findings
  │
  ├─ POST /api/judge/sessions
  │    └─ ConversationState created from analysis
  │
  └─ POST /api/judge/sessions/{id}/messages
       └─ ToolBased/Hybrid/Graph ConversationAgent handles follow-up
```

## 5. Resource Model

## 5.1 Reference Run

Reference Agent 실행 단위다. fixture run, custom analysis, chat turn을 모두 포함한다.

```ts
type ReferenceRun = {
  id: string;
  mode: 'fixture' | 'custom-analysis' | 'chat';
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  fixtureId?: string;
  userInput?: string;
  accessLogPath?: string;
  useLlm: boolean;
  tracePath?: string;
  reportPath?: string;
  sessionPath?: string;
  eventCounts: Record<string, number>;
  timelinePreview: ReferenceTimelineEvent[];
  error?: ApiError;
  createdAt: string;
  updatedAt: string;
};
```

## 5.2 Analysis

Judge Agent 분석 결과 단위다.

```ts
type Analysis = {
  id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  source: {
    kind: 'trace-paths' | 'reference-run' | 'upload';
    tracePaths: string[];
    referenceRunId?: string;
  };
  adapter: string;
  summary: AnalysisSummary;
  results: AnalysisResultDto[];
  findings: FindingDto[];
  reportMarkdown?: string;
  error?: ApiError;
  createdAt: string;
  updatedAt: string;
};
```

## 5.3 Judge Session

대화형 Judge Agent session이다. `ConversationState`의 API-safe projection이다.

```ts
type JudgeSession = {
  id: string;
  mode: 'deterministic-v2' | 'hybrid' | 'graph';
  analysisId?: string;
  loadedTraces: string[];
  messages: ChatMessageDto[];
  focus: {
    runId?: string;
    findingId?: string;
    metric?: string;
  };
  toolCalls: ToolCallDto[];
  evidence: EvidenceDto[];
  createdAt: string;
  updatedAt: string;
};
```

## 6. Endpoint 설계

## 6.1 System / Config

### `GET /api/health`

Response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "runtime": "file-backed",
  "time": "2026-05-15T13:20:00Z"
}
```

### `GET /api/config`

프론트 설정 화면과 초기 capability check에 사용한다.

Response:

```json
{
  "configDir": "simple/config",
  "appDefaults": {
    "adapter": "reference-weblog-jsonl",
    "chatMode": "deterministic",
    "failOn": "critical"
  },
  "supported": {
    "chatModes": ["deterministic", "deterministic-v2", "hybrid", "graph"],
    "llmProviders": ["auto", "openai", "ollama", "mock", "none"]
  },
  "llm": {
    "provider": "ollama",
    "model": "qwen3.5:latest",
    "apiKeyConfigured": false
  },
  "metrics": {
    "count": 35
  }
}
```

## 6.2 Reference Agent APIs

### `GET /api/reference/fixtures`

`reference_agent.weblog_agent.fixtures.fixtures()` 기반.

Response:

```json
{
  "fixtures": [
    {
      "id": "normal-login-error-spike",
      "label": "Normal login error spike",
      "userInput": "지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요",
      "accessLogPath": "reference_agent/weblog_agent/fixtures/access.log",
      "fault": null
    }
  ]
}
```

### `POST /api/reference/runs`

Reference Agent fixture/custom analysis/chat turn 실행.

Request — fixture:

```json
{
  "mode": "fixture",
  "fixtureId": "normal-login-error-spike",
  "useLlm": false,
  "outputDir": "artifacts/frontend/reference-runs"
}
```

Request — custom analysis:

```json
{
  "mode": "custom-analysis",
  "userInput": "지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요",
  "accessLogPath": "reference_agent/weblog_agent/fixtures/access.log",
  "useLlm": false
}
```

Request — chat turn:

```json
{
  "mode": "chat",
  "sessionId": "login-incident",
  "userInput": "방금 결과에서 가장 의심되는 원인은?",
  "accessLogPath": "reference_agent/weblog_agent/fixtures/access.log",
  "useLlm": false
}
```

Response:

```json
{
  "run": {
    "id": "ref_20260515_132000_normal-login-error-spike",
    "mode": "fixture",
    "status": "succeeded",
    "fixtureId": "normal-login-error-spike",
    "useLlm": false,
    "tracePath": "artifacts/frontend/reference-runs/normal-login-error-spike.jsonl",
    "reportPath": "artifacts/frontend/reference-runs/reports/normal-login-error-spike.md",
    "eventCounts": {
      "react_step": 9,
      "tool_end": 7,
      "validation_result": 1
    },
    "timelinePreview": []
  }
}
```

Implementation note:

- 1차는 sync response로 충분하다.
- LLM 사용 시 latency가 길어지면 Phase 2에서 background task + polling/SSE로 전환한다.
- 기존 `run_fixture`, `run_analysis`는 직접 호출 가능하다.
- `run_chat`은 현재 stdin loop 중심이므로 API용 `ChatAgent.handle_user_turn()` service wrapper를 별도로 만든다.

### `GET /api/reference/runs`

file-backed registry에서 최근 run 목록 반환.

### `GET /api/reference/runs/{run_id}`

run metadata + report excerpt 반환.

### `GET /api/reference/runs/{run_id}/trace`

JSONL trace를 event list로 변환해 반환한다. 긴 raw trace는 pagination을 둔다.

Query:

```text
?offset=0&limit=200&type=tool_end
```

Response:

```json
{
  "runId": "ref_...",
  "tracePath": "...jsonl",
  "events": [
    {"index": 0, "type": "run_start", "raw": {}}
  ],
  "nextOffset": 200
}
```

## 6.3 Judge Analysis APIs

### `POST /api/analyses`

Trace를 분석해 Analysis resource를 만든다.

Request — trace paths:

```json
{
  "source": {
    "kind": "trace-paths",
    "tracePaths": ["artifacts/frontend/reference-runs/normal-login-error-spike.jsonl"]
  },
  "adapter": "reference-weblog-jsonl",
  "failOn": "critical"
}
```

Request — reference run:

```json
{
  "source": {
    "kind": "reference-run",
    "referenceRunId": "ref_20260515_132000_normal-login-error-spike"
  },
  "adapter": "reference-weblog-jsonl"
}
```

Response:

```json
{
  "analysis": {
    "id": "ana_20260515_132030",
    "status": "succeeded",
    "summary": {
      "runCount": 1,
      "gateCounts": {"pass": 0, "warning": 0, "block": 1},
      "severityCounts": {"critical": 1, "high": 1, "medium": 0, "low": 0},
      "topFindings": []
    },
    "findings": []
  }
}
```

Implementation note:

- 내부적으로 `analyze_traces(trace_paths, adapter_name=adapter)` 사용.
- `AnalysisResult.to_dict()`를 API DTO로 normalize.
- `markdown_report(results)`도 함께 생성해 report tab에서 볼 수 있게 한다.

### `GET /api/analyses`

최근 analysis 목록.

### `GET /api/analyses/{analysis_id}`

analysis detail.

### `GET /api/analyses/{analysis_id}/findings/{finding_id}`

finding detail + evidence.

## 6.4 Judge Conversation APIs

### `POST /api/judge/sessions`

Analysis를 기반으로 대화형 session 생성.

Request:

```json
{
  "analysisId": "ana_20260515_132030",
  "sessionId": "weblog-drift-review",
  "mode": "deterministic-v2",
  "llm": {
    "provider": "none",
    "model": null
  }
}
```

Response:

```json
{
  "session": {
    "id": "weblog-drift-review",
    "mode": "deterministic-v2",
    "analysisId": "ana_20260515_132030",
    "loadedTraces": ["...jsonl"],
    "messages": [],
    "focus": {"findingId": "JD-001", "metric": "validation_path_coverage"}
  }
}
```

Implementation note:

- `ConversationState(session_id)` 생성.
- `state.analysis_results = [result.to_dict(), ...]` 또는 `ToolBasedConversationAgent.load_analysis(trace_paths)` 사용.
- session은 `save_conversation_state()`로 file-backed 저장.

### `POST /api/judge/sessions/{session_id}/messages`

사용자 turn 처리.

Request:

```json
{
  "content": "왜 block이야?",
  "context": {
    "findingId": "JD-001",
    "metric": "validation_path_coverage"
  }
}
```

Response:

```json
{
  "message": {
    "id": "msg_...",
    "role": "assistant",
    "content": "block의 직접 원인은 critical finding...",
    "focusedFindingId": "JD-001",
    "focusedMetric": "validation_path_coverage",
    "toolCalls": [
      {
        "name": "explain_gate",
        "status": "success",
        "summary": "block 1개, warning 0개"
      }
    ]
  },
  "session": {}
}
```

Implementation note:

- mode에 따라 `ToolBasedConversationAgent`, `HybridConversationAgent`, `GraphConversationAgent` 생성.
- `agent.handle_user_turn(content)` 호출.
- `state.tool_calls[-N:]`, `state.focus`, `state.evidence`를 response에 포함.

### `GET /api/judge/sessions`

file-backed conversation session list.

### `GET /api/judge/sessions/{session_id}`

session detail.

### `GET /api/judge/sessions/{session_id}/stream`

Phase 2. SSE streaming. MVP에서는 제외 가능.

## 7. API Store 설계

MVP는 file-backed registry를 사용한다.

```text
artifacts/frontend-api/
  reference-runs/
    registry.json
    traces/*.jsonl
    reports/*.md
  analyses/
    registry.json
    ana_*.json
    ana_*.md
  judge-sessions/
    *.conversation.json
```

`api_store.py` 책임:

- id 생성
- registry read/write
- path resolve
- artifact existence check
- API-safe serialization

DB 전환 시 테이블 후보:

| Resource | Table |
| --- | --- |
| ReferenceRun | `reference_agent_runs` |
| TraceEvent | `trace_events` |
| Analysis | `judge_analyses` |
| Finding | `judge_findings` |
| JudgeSession | `judge_sessions` |
| ChatMessage | `judge_messages` |
| ToolCall | `judge_tool_calls` |
| Evidence | `judge_evidence` |

## 8. Frontend 변경 계획

현재 `frontend/app/src/api/judgeClient.ts`는 mock export만 제공한다. 다음 단계에서 실제 client로 분리한다.

```text
src/api/
  client.ts          # fetch wrapper, error handling
  referenceApi.ts    # fixtures/runs/trace
  analysisApi.ts     # analyses/findings
  sessionApi.ts      # judge sessions/messages
  mockData.ts        # story/demo fallback
```

환경변수:

```ts
const API_BASE_URL = import.meta.env.VITE_JUDGE_API_BASE_URL ?? 'http://localhost:8787';
```

상태 구조:

```text
state/
  useReferenceRuns.ts
  useAnalyses.ts
  useJudgeSession.ts
```

1차는 React hooks + local component state로 충분하다. 상태가 복잡해지면 Zustand를 도입한다.

## 9. Error Contract

모든 실패는 같은 형태로 반환한다.

```json
{
  "error": {
    "code": "REFERENCE_FIXTURE_NOT_FOUND",
    "message": "Unknown fixture: foo",
    "detail": {
      "fixtureId": "foo"
    }
  }
}
```

권장 error code:

| Code | Case |
| --- | --- |
| `BAD_REQUEST` | request validation 실패 |
| `REFERENCE_FIXTURE_NOT_FOUND` | fixture id 없음 |
| `REFERENCE_RUN_FAILED` | reference runtime 실패 |
| `TRACE_NOT_FOUND` | trace path 없음 |
| `ANALYSIS_FAILED` | judge analysis 실패 |
| `SESSION_NOT_FOUND` | session id 없음 |
| `LLM_UNAVAILABLE` | hybrid/graph LLM provider unavailable |

## 10. 보안/안전 고려

- Path input은 repo/artifacts allowlist 안으로 제한한다.
- API key/env secret은 response에 포함하지 않는다.
- 임의 shell command 실행 API를 만들지 않는다.
- Reference Agent 실행은 정해진 fixture/custom analysis function만 허용한다.
- 업로드 파일은 크기 제한과 `.jsonl` 확장자 검증을 둔다.
- CORS는 local dev origin만 허용한다.

MVP allowlist 후보:

```text
reference_agent/weblog_agent/fixtures/
reference_agent/weblog_agent/traces/
reference_agent/weblog_agent/reports/
artifacts/
```

## 11. 구현 단계

## Phase A — API Skeleton

작업:

- [ ] `api_models.py` Pydantic DTO 추가
- [ ] `api_store.py` file-backed registry 추가
- [ ] `api_services.py` orchestration skeleton 추가
- [ ] `api.py` FastAPI app 추가
- [ ] `/api/health`, `/api/config`, `/api/reference/fixtures`, `/api/metrics` 구현

검증:

- [ ] `python3 -m unittest discover -s simple/judge_agent_simple/tests`
- [ ] `uvicorn simple.judge_agent_simple.api:app --port 8787`
- [ ] `curl http://localhost:8787/api/health`

## Phase B — Reference Agent API

작업:

- [ ] fixture run API 구현
- [ ] custom analysis API 구현
- [ ] reference run registry 저장
- [ ] trace event count/timeline preview 생성
- [ ] trace pagination endpoint 구현

검증:

- [ ] `POST /api/reference/runs` with `normal-login-error-spike`
- [ ] trace/report 파일 생성 확인
- [ ] `GET /api/reference/runs/{id}/trace` event 반환 확인

## Phase C — Judge Analysis API

작업:

- [ ] `POST /api/analyses` 구현
- [ ] referenceRunId → tracePath resolve
- [ ] `analyze_traces()` 호출
- [ ] summary/finding DTO 생성
- [ ] markdown report artifact 저장

검증:

- [ ] reference run trace를 analysis로 연결
- [ ] block/warning/pass summary 확인
- [ ] finding evidence가 frontend DTO로 노출되는지 확인

## Phase D — Judge Session API

작업:

- [ ] `POST /api/judge/sessions` 구현
- [ ] `POST /api/judge/sessions/{id}/messages` 구현
- [ ] deterministic-v2 우선 연결
- [ ] hybrid/graph mode optional 연결
- [ ] session list/detail 구현

검증:

- [ ] session 생성
- [ ] “왜 block이야?” 요청/응답
- [ ] `toolCalls`, `focus`, `evidence` response 확인

## Phase E — Frontend Real API 연결

작업:

- [ ] mock `judgeClient.ts`를 real client + mock fallback으로 분리
- [ ] Reference Agent Lab에서 fixture 목록 API 사용
- [ ] `Run reference agent` 버튼을 `POST /api/reference/runs`에 연결
- [ ] `Judge this trace` 버튼을 `POST /api/analyses`에 연결
- [ ] ChatPanel을 `POST /api/judge/sessions/{id}/messages`에 연결
- [ ] loading/error/empty state 추가

검증:

- [ ] `npm run build`
- [ ] browser에서 full flow 수동 검증

## Phase F — Streaming / Background Jobs

MVP 이후.

작업:

- [ ] long-running run을 background job으로 전환
- [ ] `GET /api/jobs/{id}` 또는 run resource polling 추가
- [ ] SSE endpoint로 chat response/tool call stream 제공

## 12. MVP API 우선순위

가장 먼저 구현할 최소 endpoint:

1. `GET /api/health`
2. `GET /api/config`
3. `GET /api/reference/fixtures`
4. `POST /api/reference/runs` fixture mode only
5. `POST /api/analyses`
6. `POST /api/judge/sessions`
7. `POST /api/judge/sessions/{session_id}/messages`

이 7개만 있으면 현재 mock 프론트의 핵심 flow를 실제 runtime으로 교체할 수 있다.

## 13. 프론트와 API 간 이벤트 매핑

| UI Action | API Call | Backend Runtime |
| --- | --- | --- |
| 화면 초기화 | `GET /api/config`, `GET /api/reference/fixtures` | config loader, fixtures registry |
| Run reference agent | `POST /api/reference/runs` | `WebLogAnalysisAgent.run()` / fixture wrapper |
| View trace timeline | `GET /api/reference/runs/{id}/trace` | JSONL parser |
| Judge this trace | `POST /api/analyses` | `analyze_traces()` |
| Create chat review | `POST /api/judge/sessions` | `ConversationState` + selected agent |
| Ask question | `POST /api/judge/sessions/{id}/messages` | `handle_user_turn()` |

## 14. 완료 기준

API 연동 1차 완료 기준:

- Reference Agent fixture를 UI 버튼으로 실행할 수 있다.
- 생성된 trace/report 경로가 UI에 표시된다.
- 해당 trace를 Judge Agent가 분석한다.
- findings가 mock이 아니라 API response에서 렌더링된다.
- 사용자가 “왜 block이야?”를 입력하면 실제 `ToolBasedConversationAgent` 응답이 표시된다.
- Python tests와 frontend build가 통과한다.
