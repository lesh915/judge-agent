# Web Log Analysis Reference Agent Docs

이 폴더는 Judge Agent 개발 전 테스트/레퍼런스 대상으로 사용할 Web Log Analysis Agent 개발 문서를 포함한다.

## 문서 목록

- `PRD.md` — 제품 요구사항
- `DEVELOPMENT_GUIDE.md` — 구현 가이드
- `SYSTEM_DESIGN.md` — 시스템 설계
- `ARCHITECTURE.md` — 아키텍처
- `BACKEND_API.md` — 백엔드 API 설계
- `FRONTEND.md` — 프론트엔드 설계

## 목적

이 에이전트는 LangChain/LangGraph 기반 웹로그 분석 agent이며, Judge Agent가 drift를 탐지하기 위한 reference trace와 fixture를 생성한다.

## 현재 기준: ReAct Reference Agent

Reference agent는 다음을 반드시 포함한다.

- LangGraph-style graph node/edge
- LLM 기반 ReAct decision
- Prompt bundle: system, ReAct protocol, tool policy, output contract
- Log analysis tools
- RAG runbook retriever
- MCP service-context client
- validation node
- JSONL trace

즉, Judge Agent의 target은 “일반적인 AI Agent 구성요소를 가진 LangChain/LangGraph ReAct agent”다.
