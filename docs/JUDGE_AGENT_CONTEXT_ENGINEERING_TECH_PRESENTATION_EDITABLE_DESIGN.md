# Judge Agent Context Engineering 발표자료 재설계표

파일: `JUDGE_AGENT_CONTEXT_ENGINEERING_TECH_PRESENTATION_EDITABLE.pptx`  
목표: 이미지가 아닌 PowerPoint 네이티브 도형/텍스트/표/화살표로 구성된 편집 가능한 기술 세미나 자료

## 디자인 원칙

- 배경: 흰색 또는 아주 옅은 회색
- 제목: 작게, 좌상단 고정, 20pt 내외
- 본문: 12~15pt, 카드당 bullet 2~3개 제한
- 도형: 텍스트를 도형 내부에 과도하게 넣지 않고, 카드 배경 + 별도 텍스트 박스 조합
- 구조: 12-column grid에 가까운 좌표 체계, 안전 여백 유지
- 시각 요소: Architecture map, flow, matrix, state lane, event pipeline 중심
- 편집성: 모든 텍스트/도형/화살표/표는 PowerPoint에서 직접 편집 가능

## 슬라이드 구성

| # | 제목 | 목적 | 레이아웃 |
|---:|---|---|---|
| 1 | Judge Agent를 위한 Context Engineering & Drift Telemetry | 전체 주제와 3축 제시 | Title + 3 cards |
| 2 | 운영 Agent가 실패하는 지점 | drift/problem framing | 2x2 problem matrix |
| 3 | 세 문서가 만드는 운영 루프 | 문서 간 연결 설명 | 3-step architecture loop |
| 4 | Context는 계층이다 | context taxonomy | vertical layer stack |
| 5 | Context Inventory | include/select/exclude 기준 | 3x2 card grid |
| 6 | Context Packing Pipeline | prompt/context 구성 순서 | horizontal process flow |
| 7 | Write / Select / Compress / Isolate | 4대 전략 설명 | 2x2 strategy matrix |
| 8 | Long Context Failure Modes | 긴 context 실패 유형 | 2x2 risk matrix |
| 9 | LangGraph Context Flow | State/Node/Edge/Checkpoint 구조 | state lane + node flow |
| 10 | State 설계 원칙 | raw/summary/evidence 분리 | code-like schema + principles |
| 11 | Node는 Context Boundary다 | node contract 개념 | 3-column contract flow |
| 12 | Dynamic Tool Selection | tool drift 방지 | tool pipeline |
| 13 | ReAct Step 최소 Context | step context 예시 | JSON-like box + keep/drop cards |
| 14 | RAG는 Context Pipeline이다 | retrieval→validate→pack | RAG flow + source classes |
| 15 | Memory와 Checkpoint는 다르다 | memory/checkpoint 차이 | comparison lanes |
| 16 | Human-in-the-loop Gate | 승인 context pack | approval flow |
| 17 | Reference Agent Architecture | weblog agent 구조 | three-zone architecture map |
| 18 | Drift Telemetry Event Taxonomy | event가 답하는 질문 | event taxonomy table |
| 19 | Judge Agent Evaluation Loop | observe→judge→improve | circular evaluation loop |
| 20 | 구현 체크리스트와 결론 | 실무 적용 요약 | checklist + takeaway |

## 검수 기준

- [ ] PPTX 내부에 슬라이드 전체 배경 이미지 사용 금지
- [ ] PowerPoint에서 모든 텍스트 직접 편집 가능
- [ ] 제목 18~22pt 범위 유지
- [ ] 본문 주요 텍스트 11pt 미만 금지
- [ ] 카드당 bullet 3개 이하
- [ ] 슬라이드당 핵심 메시지 1개
- [ ] 구조도는 의미 있는 연결선과 라벨 포함
