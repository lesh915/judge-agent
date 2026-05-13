# Frontend: Web Log Analysis Reference Agent

## 1. 목적

Frontend는 웹로그 분석 레퍼런스 에이전트를 시각적으로 실행하고, 생성된 trace/report를 확인하기 위한 선택적 UI다.

MVP 개발에서는 필수는 아니지만, Judge Agent 데모와 trace 이해를 돕기 위해 간단한 UI를 설계한다.

## 2. 주요 화면

## 2.1 Analysis Runner

기능:

- user input 입력
- access log path 입력
- log format 선택
- baseline 선택
- run 버튼
- report 결과 표시

## 2.2 Fixture Runner

기능:

- fixture 목록 표시
- normal/drift category filter
- fixture 실행
- trace/report link 표시

## 2.3 Trace Viewer

기능:

- event timeline 표시
- node/tool event 구분
- state before/after 보기
- tool arguments/result 보기
- error event 강조

## 2.4 Report Viewer

기능:

- markdown report 표시
- evidence section 강조
- limitation section 표시

## 3. UI 정보 구조

```text
Sidebar
  - Analyze
  - Fixtures
  - Runs
  - Trace Viewer
  - Reports

Main
  - selected page content
```

## 4. 컴포넌트

- `AnalysisForm`
- `FixtureList`
- `RunSummaryCard`
- `TraceTimeline`
- `EventDetailPanel`
- `MarkdownReportViewer`
- `MetricSummary`

## 5. API 연동

사용 API:

- `POST /v1/analyze`
- `GET /v1/fixtures`
- `POST /v1/fixtures/{fixture_id}/run`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/trace`

## 6. MVP UI 범위

포함:

- fixture 실행
- report 표시
- trace timeline 표시

제외:

- 사용자 인증
- 실시간 streaming
- trace diff
- Judge Agent finding overlay

## 7. 향후 확장

- Judge Agent findings와 trace event 연결 표시
- normal vs drift trace 비교
- graph node 시각화
- metric trend chart
