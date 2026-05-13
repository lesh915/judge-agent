# Agent Drift 측정을 위한 Agent 연동 방법 가이드

## 1. 목적

Judge Agent가 drift를 탐지하려면 평가 대상 agent로부터 실행 중 발생한 측정값과 trace를 전달받아야 한다. 하지만 agent는 프레임워크, SDK, 플랫폼, 자체 구현 여부에 따라 구조가 크게 다르다.

이 문서는 다양한 agent 개발 방법론/라이브러리/플랫폼별로 다음을 정리한다.

- 어떤 데이터를 수집해야 하는가
- 어떤 hook, callback, tracing, telemetry 방식을 사용할 수 있는가
- Judge Agent가 요구하는 공통 trace schema로 어떻게 변환할 것인가
- 프레임워크별 drift 측정 시 주의할 점은 무엇인가

## 2. 웹 리서치 요약

조사 결과, 최근 agent observability는 크게 세 방향으로 수렴하고 있다.

1. **OpenTelemetry 기반 표준화**
   - OpenTelemetry GenAI semantic conventions가 LLM call, prompt, completion, token usage, tool definitions, tool calls 등을 표현하는 표준으로 확산 중이다.
   - AutoGen, Semantic Kernel, LlamaIndex, PydanticAI/Logfire, Vercel AI SDK, Mastra 등 다수가 OTel 기반 tracing을 지원하거나 연동한다.

2. **프레임워크 내장 tracing**
   - OpenAI Agents SDK는 LLM generations, tool calls, handoffs, guardrails, custom events를 trace/span으로 기록한다.
   - LangChain/LangGraph는 LangSmith를 통해 chain, graph node, tool, LLM call trace를 수집한다.
   - Mastra는 agent runs, LLM generations, tool calls, workflow steps, memory operations를 trace한다.

3. **Observability 플랫폼 연동**
   - LangSmith, Langfuse, Arize Phoenix, OpenLIT/OpenLLMetry, Traceloop, MLflow, Weave, Logfire, Datadog, New Relic, SigNoz 등이 agent trace 수집/시각화/평가를 제공한다.
   - Judge Agent는 이들 플랫폼의 export API 또는 OTLP exporter를 통해 trace를 수집할 수 있다.

주요 참고 자료:

- OpenTelemetry GenAI Semantic Conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/
- OpenAI Agents SDK Tracing: https://openai.github.io/openai-agents-python/tracing/
- LangSmith OpenTelemetry tracing: https://docs.langchain.com/langsmith/trace-with-opentelemetry
- LlamaIndex Observability: https://developers.llamaindex.ai/python/framework/module_guides/observability/
- AutoGen Tracing and Observability: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tracing.html
- CrewAI Observability: https://docs.crewai.com/en/observability/overview
- PydanticAI Logfire Integration: https://pydantic.dev/docs/ai/integrations/logfire/
- Vercel AI SDK Telemetry: https://ai-sdk.dev/docs/ai-sdk-core/telemetry
- Semantic Kernel Observability: https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/observability/
- Mastra Observability: https://mastra.ai/ai-agent-observability
- OWASP Agent Observability Standard draft: https://owasp.github.io/www-project-agent-observability-standard/spec/trace/extend_opentelemetry/

## 3. Judge Agent 공통 연동 모델

프레임워크가 무엇이든 Judge Agent는 최종적으로 아래 공통 schema를 받는 것을 목표로 한다.

### 3.1 Normalized Agent Run

```json
{
  "run_id": "string",
  "session_id": "string",
  "agent": {
    "id": "string",
    "name": "string",
    "version": "string",
    "framework": "langchain|langgraph|openai-agents|crewai|autogen|llamaindex|pydanticai|semantic-kernel|vercel-ai-sdk|mastra|custom",
    "model": "string"
  },
  "input": {
    "user_request": "string",
    "messages": []
  },
  "instructions": {
    "system": "string",
    "developer": "string",
    "agent_role": "string",
    "tool_policy": "string",
    "memory_policy": "string",
    "safety_policy": "string"
  },
  "events": [],
  "final_output": "string",
  "metadata": {
    "started_at": "ISO-8601",
    "completed_at": "ISO-8601",
    "latency_ms": 0,
    "token_usage": {},
    "cost": 0
  }
}
```

### 3.2 공통 Event Types

Judge Agent의 drift detector는 event stream을 기준으로 동작한다.

```json
{
  "event_id": "string",
  "parent_event_id": "string|null",
  "timestamp": "ISO-8601",
  "type": "message|llm_call|plan|tool_call|tool_result|context_retrieval|memory_read|memory_write|handoff|guardrail|approval|error|file_change|final_response",
  "name": "string",
  "input": {},
  "output": {},
  "metadata": {}
}
```

### 3.3 Drift 탐지에 필요한 최소 필드

| 영역 | 필수 데이터 | 탐지 가능한 drift |
|---|---|---|
| Prompt | system/developer/user instruction, selected prompt template | prompt drift, hierarchy violation |
| LLM call | model, prompt/messages, response, usage, latency | output quality, instruction adherence |
| Tool | available tools, selected tool, arguments, result, error | tool drift, argument hallucination, sequence drift |
| Context/RAG | query, retrieved chunks, scores, source ids, final context | context drift, grounding failure |
| Memory | read query, retrieved memories, write/update/delete ops | memory drift, stale memory, privacy leakage |
| Plan | generated plan, executed steps, state transitions | reasoning/trajectory drift |
| Safety | guardrail checks, approvals, blocked actions | safety/permission drift |
| Handoff | source agent, target agent, handoff reason, payload | role drift, multi-agent routing drift |
| Final output | final answer/artifact, files changed | task completion, quality drift |

## 4. 연동 방식 유형

## 4.1 Native Trace Export 방식

프레임워크가 자체 tracing/export를 제공하는 경우 사용한다.

적합한 경우:

- OpenAI Agents SDK
- LangSmith/LangGraph
- Mastra
- LlamaIndex OTel
- AutoGen OTel
- Semantic Kernel OTel
- Vercel AI SDK telemetry

구현 방법:

1. 프레임워크 내장 tracing 활성화
2. trace/span을 OTLP, JSON, API export로 수집
3. Judge Agent adapter가 Normalized Agent Run으로 변환

장점:

- 구현 부담 낮음
- tool call, LLM call, latency, usage가 자동 수집됨
- production observability와 공유 가능

단점:

- prompt/memory/safety policy 같은 고수준 의미 정보가 누락될 수 있음
- 프레임워크별 span naming과 attribute가 다름

## 4.2 Callback / Hook 방식

프레임워크가 callback, middleware, event handler를 제공하는 경우 사용한다.

적합한 경우:

- LangChain callbacks
- LlamaIndex callback manager / instrumentation
- CrewAI event/log hooks
- custom Python/TypeScript agent

구현 방법:

1. LLM start/end hook 등록
2. tool start/end/error hook 등록
3. memory read/write hook 등록
4. final response hook 등록
5. 각 hook에서 Judge Agent event를 생성

장점:

- 필요한 의미 정보를 직접 붙일 수 있음
- redaction/filtering을 세밀하게 제어 가능

단점:

- framework upgrade에 취약
- 누락 hook이 있으면 trace가 불완전해짐

## 4.3 OpenTelemetry Auto-Instrumentation 방식

OpenLLMetry, OpenInference, framework OTel instrumentor 등을 사용한다.

적합한 경우:

- LangChain/LlamaIndex/Haystack auto instrumentation
- AutoGen OTel
- Semantic Kernel OTel
- PydanticAI/Logfire
- Vercel AI SDK
- custom app with OTel spans

구현 방법:

1. OTel SDK 설정
2. instrumentor 활성화
3. OTLP collector 또는 observability backend로 export
4. Judge Agent가 OTLP 또는 backend API에서 trace 수집

장점:

- 여러 framework를 한 collector로 통합 가능
- backend, DB, HTTP call과 agent trace를 연결 가능
- vendor-neutral

단점:

- raw span만으로는 agent semantics가 부족할 수 있음
- prompt/content 기록은 privacy 때문에 opt-in인 경우가 많음

## 4.4 Proxy / Gateway 방식

LLM API, tool API, MCP server, HTTP client 앞단에 proxy를 두고 관측한다.

적합한 경우:

- framework 수정이 어려운 경우
- closed-source agent
- 여러 agent가 공통 LLM gateway를 사용하는 경우
- MCP tool server 기반 agent

구현 방법:

1. LLM gateway에서 request/response 기록
2. tool gateway에서 tool name/input/output/error 기록
3. session id / trace id를 header나 metadata로 전달
4. Judge Agent가 gateway log를 수집

장점:

- agent 코드 수정 최소화
- 여러 agent를 중앙에서 관측 가능

단점:

- agent 내부 plan, memory decision, instruction selection은 보기 어려움
- tool call의 의도나 reasoning은 별도 metadata 필요

## 4.5 Log/File Export 방식

기존 agent가 structured log만 남기는 경우 사용한다.

적합한 경우:

- legacy agent
- CLI/coding agent
- batch workflow
- 보안상 외부 telemetry가 어려운 환경

구현 방법:

1. JSONL log format 정의
2. 각 event를 한 줄씩 append
3. run 종료 후 Judge Agent CLI에 전달

장점:

- 단순하고 로컬-only 가능
- CI와 잘 맞음

단점:

- 실시간 모니터링 어려움
- 표준화되지 않은 로그는 parser 비용 증가

## 5. 프레임워크별 연동 가이드

## 5.1 LangChain / LangGraph

### 관측 방식

- LangSmith tracing
- LangSmith OpenTelemetry ingest/export
- LangChain callbacks
- LangGraph node/state trace

### 수집해야 할 값

- chain/graph run id
- node name, edge transition
- state before/after node
- LLM prompt/messages and response
- tool name, arguments, result
- retriever query, retrieved documents, scores
- memory load/save events
- errors, retries

### Judge Agent adapter 전략

LangSmith run tree 또는 OTel span tree를 Normalized Agent Run으로 변환한다.

Mapping:

| LangChain/LangGraph | Judge Event |
|---|---|
| LLM run | `llm_call` |
| Tool run | `tool_call` + `tool_result` |
| Retriever run | `context_retrieval` |
| Chain/Graph node | `plan` 또는 `state_transition` |
| Callback error | `error` |
| LangGraph checkpoint/state | `memory_read` 또는 `context_state` |

### Drift 탐지 포인트

- graph edge가 예상 workflow에서 벗어났는가
- 같은 node/tool을 반복했는가
- retriever 결과와 final answer가 충돌하는가
- checkpoint state에 오래된 값이 남아 drift를 유발했는가
- tool arguments가 state/context에서 온 값인지 확인 가능한가

### 권장 연동 수준

- MVP: LangSmith trace export
- 권장: LangSmith + custom metadata로 instruction/version/tool policy 추가
- 고급: LangGraph state checkpoint를 함께 export

## 5.2 OpenAI Agents SDK

### 관측 방식

- SDK built-in tracing
- trace/span export
- custom spans
- guardrail/handoff/tool traces

OpenAI Agents SDK는 agent run 중 LLM generation, tool call, handoff, guardrail, custom event를 trace로 기록한다.

### 수집해야 할 값

- agent name/instructions
- Runner run id
- LLM generation input/output
- tool calls and tool outputs
- handoffs between agents
- guardrail checks and results
- session state
- trace include sensitive data 설정 여부

### Judge Agent adapter 전략

SDK trace를 받아 다음으로 매핑한다.

| Agents SDK | Judge Event |
|---|---|
| generation span | `llm_call` |
| tool span | `tool_call` / `tool_result` |
| handoff span | `handoff` |
| guardrail span | `guardrail` |
| custom span | custom event |

### Drift 탐지 포인트

- handoff가 user intent와 맞는 target agent로 갔는가
- guardrail이 trigger되었는데 agent가 계속 진행했는가
- tool call이 instructions/tool policy와 일치하는가
- sensitive trace 설정 때문에 필요한 evidence가 누락되었는가

### 권장 연동 수준

- MVP: built-in tracing export
- 권장: custom span으로 memory/context/approval event 추가

## 5.3 CrewAI

### 관측 방식

- CrewAI observability integrations
- LangDB, OpenLIT, MLflow, Langtrace, Arize Phoenix, Portkey, Weave 등
- Patronus AI evaluation integration
- task/agent execution logs

### 수집해야 할 값

- crew id, agent id, role, goal, backstory
- task description and expected output
- agent thought/action/observation logs
- tool calls and outputs
- delegation events
- task final output
- quality evaluator results if available

### Judge Agent adapter 전략

CrewAI는 role/goal/task 중심 구조이므로 다음 mapping을 사용한다.

| CrewAI | Judge Event |
|---|---|
| Agent role/goal/backstory | `instructions.agent_role` |
| Task description | `input.user_request` 또는 `task` |
| Expected output | reference criteria |
| Tool action | `tool_call` |
| Observation | `tool_result` |
| Delegation | `handoff` |
| Task output | `final_response` |

### Drift 탐지 포인트

- agent role/goal에서 벗어난 행동을 했는가
- expected output과 final output이 일치하는가
- delegation이 필요한 상황에서 누락되었거나 불필요하게 발생했는가
- crew 내 agent 간 task boundary가 무너졌는가

### 권장 연동 수준

- MVP: observability provider export 또는 structured execution log
- 권장: task expected_output을 Judge reference로 전달

## 5.4 Microsoft AutoGen / AG2

### 관측 방식

- AutoGen built-in tracing and observability
- OpenTelemetry backend 연동
- AG2 OpenTelemetry tracing
- conversation, agent turn, LLM call, tool execution, speaker selection spans

### 수집해야 할 값

- conversation id
- agent turn
- speaker selection
- LLM calls
- tool execution
- code execution
- human input request
- inter-agent messages
- termination condition

### Judge Agent adapter 전략

| AutoGen/AG2 | Judge Event |
|---|---|
| conversation span | run/session |
| agent span | `agent_turn` |
| llm span | `llm_call` |
| tool/code execution span | `tool_call` / `tool_result` |
| human input span | `approval` 또는 `human_input` |
| speaker selection | `handoff` 또는 `routing` |

### Drift 탐지 포인트

- speaker selection이 잘못되어 적절하지 않은 agent가 응답했는가
- multi-agent loop가 발생했는가
- code execution 결과를 잘못 해석했는가
- human input이 필요한 순간에 자동 진행했는가

### 권장 연동 수준

- MVP: OTel trace export
- 권장: speaker selection rationale를 custom attribute로 추가

## 5.5 LlamaIndex Agents

### 관측 방식

- LlamaIndex observability integrations
- OpenTelemetry integration
- legacy CallbackManager / global handler
- RAG pipeline event tracing

### 수집해야 할 값

- query
- agent reasoning steps
- tool calls
- retriever queries
- retrieved nodes/documents
- similarity scores
- synthesized response
- memory operations if used

### Judge Agent adapter 전략

LlamaIndex는 RAG/context 품질 평가가 특히 중요하다.

| LlamaIndex | Judge Event |
|---|---|
| query engine call | `context_retrieval` + `llm_call` |
| retriever event | `context_retrieval` |
| node/document | retrieved context chunk |
| tool call | `tool_call` |
| response synthesis | `llm_call` / `final_response` |

### Drift 탐지 포인트

- retrieved node가 query와 관련 있는가
- source node와 final answer가 faithfulness를 만족하는가
- 낮은 score context를 과신했는가
- 필요한 document가 누락되었는가

### 권장 연동 수준

- MVP: OTel trace + retrieved node export
- 권장: source id, score, chunk text, metadata 필수 전달

## 5.6 PydanticAI

### 관측 방식

- Pydantic Logfire integration
- OpenTelemetry export
- agent run trace
- model request spans
- tool call spans

### 수집해야 할 값

- agent name/instructions
- dependencies/deps context
- model request/response
- tool call input/output
- usage/cost/latency
- validation errors
- structured output validation result

### Judge Agent adapter 전략

| PydanticAI/Logfire | Judge Event |
|---|---|
| agent run trace | run/session |
| model request span | `llm_call` |
| tool call span | `tool_call` / `tool_result` |
| validation error | `error` / `format_violation` |
| structured result | `final_response` |

### Drift 탐지 포인트

- structured output schema를 위반했는가
- tool return type / output validation 실패를 무시했는가
- deps context에 없는 값을 생성했는가

### 권장 연동 수준

- MVP: Logfire/OTel trace export
- 권장: validation errors를 Judge finding evidence로 전달

## 5.7 Semantic Kernel

### 관측 방식

- OpenTelemetry-compatible logs, metrics, traces
- kernel/plugin/function execution telemetry
- AI connector token usage and latency

### 수집해야 할 값

- kernel function name
- plugin/function arguments
- function result
- planner output if used
- AI connector request/response
- token usage
- errors

### Judge Agent adapter 전략

| Semantic Kernel | Judge Event |
|---|---|
| kernel function execution | `tool_call` |
| plugin call | `tool_call` |
| AI connector span | `llm_call` |
| planner output | `plan` |
| logs/errors | `error` |

### Drift 탐지 포인트

- planner가 부적절한 plugin/function을 선택했는가
- function arguments가 semantic context와 맞는가
- plugin result를 잘못 해석했는가

### 권장 연동 수준

- MVP: OTel traces/logs
- 권장: planner output과 plugin manifest를 함께 전달

## 5.8 Vercel AI SDK

### 관측 방식

- `experimental_telemetry`
- OpenTelemetry spans
- `ai.generateText`, `ai.streamText`, `ai.toolCall` spans
- prompt/output/token/tool details opt-in

### 수집해야 할 값

- functionId
- metadata
- prompt/messages
- generated text/stream result
- tool calls
- tool outputs
- usage
- streaming first chunk latency

### Judge Agent adapter 전략

| Vercel AI SDK | Judge Event |
|---|---|
| `ai.generateText` span | `llm_call` |
| `ai.streamText` span | `llm_call` |
| `ai.toolCall` span | `tool_call` / `tool_result` |
| metadata | run metadata |

### Drift 탐지 포인트

- streaming 중 tool call loop가 발생했는가
- tool call details가 final answer에 반영되었는가
- structured output generation 실패가 있었는가

### 권장 연동 수준

- MVP: per-call telemetry 활성화
- 권장: `functionId`를 agent/run/route 식별자로 표준화

## 5.9 Haystack

### 관측 방식

- OpenTelemetry / OpenLLMetry / Traceloop
- Arize Phoenix integration
- pipeline component traces

### 수집해야 할 값

- pipeline run id
- component name
- retriever input/output
- prompt builder output
- generator input/output
- document scores
- tool/agent component calls

### Judge Agent adapter 전략

| Haystack | Judge Event |
|---|---|
| retriever component | `context_retrieval` |
| prompt builder | `prompt_build` |
| generator | `llm_call` |
| pipeline component | `state_transition` |

### Drift 탐지 포인트

- retriever context quality
- prompt builder가 잘못된 context를 포함했는가
- generator가 retrieved documents에 faithful한가

### 권장 연동 수준

- MVP: OpenTelemetry instrumentation
- 권장: document id/score/content metadata export

## 5.10 Mastra

### 관측 방식

- Mastra Observability
- OpenTelemetry-compatible exporters
- agent run, LLM generation, tool call, workflow step traces
- memory operations trace
- scorers

### 수집해야 할 값

- agent run id
- decision path
- tool calls
- memory read/write operations
- workflow steps
- scorer results
- sensitive data filter status

### Judge Agent adapter 전략

| Mastra | Judge Event |
|---|---|
| agent run | run/session |
| LLM generation | `llm_call` |
| tool call | `tool_call` / `tool_result` |
| workflow step | `state_transition` |
| memory operation | `memory_read` / `memory_write` |
| scorer | prior evaluation signal |

### Drift 탐지 포인트

- memory operation의 정확성
- shared resource/thread memory 오염 여부
- observational memory가 잘못된 요약/관찰을 생성했는가
- workflow step이 예상 경로에서 벗어났는가

### 권장 연동 수준

- MVP: Mastra trace export
- 권장: memory operation과 scorer 결과를 Judge Agent에 함께 전달

## 5.11 MCP 기반 Agent

### 관측 방식

- MCP client/server proxy logging
- tool server request/response wrapping
- OpenTelemetry custom spans

### 수집해야 할 값

- MCP server name/version
- tool list and schemas
- tool invocation name
- arguments
- result/error
- resource access
- approval/permission event

### Judge Agent adapter 전략

MCP tool call은 framework와 독립적으로 `tool_call` / `tool_result` event로 변환한다.

### Drift 탐지 포인트

- tool schema와 argument mismatch
- MCP resource access 권한 위반
- tool description을 잘못 해석한 호출
- tool result를 반영하지 않은 final answer

### 권장 연동 수준

- MVP: MCP proxy log
- 권장: server-side OTel spans + client trace id propagation

## 5.12 자체 구현 Custom Agent

### 관측 방식

- 직접 event emitter 구현
- JSONL log
- OpenTelemetry manual spans
- LLM/tool wrapper

### 최소 구현 포인트

1. Agent run 시작/종료
2. Instruction bundle snapshot
3. LLM request/response
4. Tool call/result/error
5. Context retrieval
6. Memory read/write/update/delete
7. Approval/guardrail
8. Final response

### 권장 JSONL 포맷

```jsonl
{"type":"run_start","run_id":"r1","agent":{"name":"support-agent","version":"1.2.0"}}
{"type":"instruction_snapshot","run_id":"r1","system":"...","developer":"..."}
{"type":"llm_call","run_id":"r1","event_id":"e1","model":"gpt-4.1","input":{"messages":[]},"output":{"text":"..."},"usage":{}}
{"type":"tool_call","run_id":"r1","event_id":"e2","tool":"search","arguments":{"query":"..."}}
{"type":"tool_result","run_id":"r1","parent_event_id":"e2","output":{"results":[]}}
{"type":"memory_read","run_id":"r1","query":"...","results":[]}
{"type":"final_response","run_id":"r1","content":"..."}
```

### Drift 탐지 포인트

Custom agent는 trace 누락이 가장 큰 리스크다. Judge Agent는 missing observability 자체를 finding으로 기록해야 한다.

## 6. Observability Platform별 연동

## 6.1 LangSmith

- LangChain/LangGraph에 가장 적합
- run tree, datasets, evaluators, feedback 수집 가능
- Judge Agent는 LangSmith API export 또는 OTel ingest/export를 통해 trace 수집

## 6.2 Langfuse

- OpenTelemetry 및 다양한 framework integration 지원
- prompt, generation, score, trace 관리 가능
- Judge Agent는 Langfuse trace API 또는 export 기능 사용

## 6.3 Arize Phoenix / OpenInference

- RAG/LLM trace와 evaluation에 강점
- retriever, embedding, LLM, tool trace 수집
- Judge Agent는 Phoenix trace export 또는 OpenInference span을 수집

## 6.4 OpenLIT / OpenLLMetry / Traceloop

- auto-instrumentation 중심
- LangChain, LlamaIndex, Haystack 등 Python framework에 유용
- OTel collector를 통해 Judge Agent와 연결

## 6.5 Pydantic Logfire

- PydanticAI, Vercel AI SDK, OTel-compatible apps에 유용
- conversation panel, token/cost/tool inspection 제공
- SQL/API 기반으로 Judge Agent가 trace를 조회 가능

## 6.6 Datadog / New Relic / SigNoz / Grafana Tempo

- production observability stack과 통합할 때 유용
- OTLP trace export를 표준 수집 경로로 사용
- Judge Agent는 특정 trace id 기준으로 span tree를 가져와 분석

## 7. Judge Agent Adapter 설계

## 7.1 Adapter Interface

```ts
interface AgentTraceAdapter {
  framework: string;
  detect(input: unknown): boolean;
  normalize(input: unknown): NormalizedAgentRun;
  validate(run: NormalizedAgentRun): ValidationResult;
}
```

## 7.2 Adapter 종류

- `LangSmithAdapter`
- `OpenAIAgentsAdapter`
- `CrewAIAdapter`
- `AutoGenOtelAdapter`
- `LlamaIndexAdapter`
- `PydanticAIAdapter`
- `SemanticKernelAdapter`
- `VercelAISDKAdapter`
- `HaystackAdapter`
- `MastraAdapter`
- `MCPProxyAdapter`
- `JsonlAdapter`
- `GenericOtelGenAIAdapter`

## 7.3 Generic OTel GenAI Mapping

OpenTelemetry GenAI convention 기반으로 최소 매핑한다.

| OTel Attribute / Span | Judge Field |
|---|---|
| trace_id | `run_id` |
| span_id | `event_id` |
| parent_span_id | `parent_event_id` |
| `gen_ai.provider.name` | `agent.provider` |
| `gen_ai.request.model` | `agent.model` |
| `gen_ai.response.model` | `metadata.response_model` |
| `gen_ai.usage.input_tokens` | `metadata.token_usage.input` |
| `gen_ai.usage.output_tokens` | `metadata.token_usage.output` |
| `gen_ai.system_instructions` | `instructions.system` |
| `gen_ai.tool.definitions` | available tools |
| tool span name / attributes | `tool_call` |
| span events with prompts/completions | `llm_call.input/output` |

## 8. Drift 측정을 위한 필수 Telemetry Checklist

Agent 구현체가 Judge Agent와 잘 연동되려면 아래 checklist를 만족해야 한다.

### 필수

- [ ] run/session id
- [ ] agent name/version/framework
- [ ] user request
- [ ] final response
- [ ] LLM call input/output 또는 redacted summary
- [ ] tool call name/arguments/result/error
- [ ] timestamp and parent-child relationship
- [ ] errors/retries

### 권장

- [ ] system/developer instruction snapshot
- [ ] prompt template version
- [ ] available tool definitions
- [ ] memory read/write events
- [ ] retrieved context chunks and scores
- [ ] plan/step events
- [ ] approval/guardrail events
- [ ] token usage/cost/latency
- [ ] model/provider/config

### 고급

- [ ] expected trajectory or reference output
- [ ] baseline run id
- [ ] user feedback
- [ ] evaluator/scorer results
- [ ] state checkpoints
- [ ] handoff/routing rationale
- [ ] redaction metadata

## 9. Case별 권장 연동 방식

| Agent 구현 상태 | 권장 연동 | 이유 |
|---|---|---|
| LangChain/LangGraph 기반 | LangSmith + OTel + custom metadata | trace와 eval 생태계가 가장 성숙 |
| OpenAI Agents SDK 기반 | built-in tracing + custom spans | tool/handoff/guardrail trace가 내장됨 |
| CrewAI 기반 | observability provider + task expected_output export | role/goal/task 중심 평가 필요 |
| AutoGen/AG2 기반 | OTel trace + speaker selection metadata | multi-agent routing drift 탐지 필요 |
| LlamaIndex/RAG agent | OTel + retrieved node export | context faithfulness 평가 핵심 |
| PydanticAI | Logfire/OTel + validation errors | structured output drift 탐지에 유리 |
| Semantic Kernel | OTel + planner/plugin telemetry | function/plugin selection 평가 필요 |
| Vercel AI SDK | experimental_telemetry + functionId | JS/edge 환경 trace 수집 용이 |
| Mastra | Mastra tracing + memory operations | memory/workflow drift 평가에 유리 |
| MCP tool-heavy agent | MCP proxy + OTel spans | framework 독립 tool drift 탐지 가능 |
| 자체 구현 agent | JSONL + manual OTel spans | 최소 표준부터 맞추기 쉬움 |
| closed-source agent | LLM/tool gateway proxy | 내부 수정 없이 관측 가능 |

## 10. Privacy / Security 고려사항

Trace에는 prompt, memory, tool arguments, 사용자 데이터가 포함될 수 있다.

권장 정책:

- 기본값은 content redaction 활성화
- Judge에 필요한 최소 excerpt만 저장
- sensitive field allowlist/denylist 적용
- 외부 observability provider 전송 전 사용자/조직 승인
- memory snapshot 전체 대신 referenced memory만 전달
- tool result 중 secret/token/key는 마스킹
- trace retention 기간 설정

OpenAI Agents SDK 등 일부 프레임워크는 sensitive trace 포함 여부를 설정할 수 있으므로, 운영 환경에서는 기본적으로 비활성화하거나 redaction processor를 둔다.

## 11. 연동 성숙도 모델

### Level 0 — Output Only

- final response만 평가
- 가능한 탐지: 응답 품질, 일부 instruction drift
- 한계: tool/memory/context drift 탐지 불가

### Level 1 — LLM + Tool Trace

- LLM calls와 tool calls 수집
- 가능한 탐지: tool selection, argument drift, output grounding

### Level 2 — Context / Memory Trace

- retrieved context, memory read/write 수집
- 가능한 탐지: context drift, memory drift, stale memory, hallucinated memory

### Level 3 — Full Trajectory

- plan, state transition, guardrail, approval, handoff 포함
- 가능한 탐지: reasoning drift, goal drift, safety drift, multi-agent drift

### Level 4 — Baseline + Online Monitoring

- production trace + baseline comparison + alerting
- 가능한 탐지: regression, long-term drift trend, framework/model change impact

## 12. 구현 우선순위

### Phase 1: 공통 schema와 JSONL adapter

- Normalized Agent Run schema 확정
- JSONL parser 구현
- Generic OTel GenAI adapter 구현

### Phase 2: 주요 framework adapter

1. LangSmith/LangGraph
2. OpenAI Agents SDK
3. LlamaIndex
4. AutoGen OTel
5. Vercel AI SDK

### Phase 3: Memory/tool-heavy adapter

1. Mastra
2. MCP Proxy
3. CrewAI
4. Semantic Kernel
5. PydanticAI

### Phase 4: Observability backend connector

- LangSmith API
- Langfuse API
- Phoenix/OpenInference
- OTLP collector ingestion
- Logfire query/export

## 13. Judge Agent가 연동 실패를 다루는 방식

Agent trace가 불완전할 경우 Judge Agent는 평가를 중단하지 않고 다음처럼 degradation 처리한다.

| 누락 데이터 | 처리 방식 |
|---|---|
| instruction 없음 | prompt drift confidence 낮춤, missing instruction finding |
| tool result 없음 | tool output grounding 평가 불가 표시 |
| memory trace 없음 | memory drift 평가 unavailable |
| context chunk 없음 | faithfulness 대신 answer relevance만 평가 |
| parent-child 관계 없음 | sequence/trajectory 평가 제한 |
| final output 없음 | run incomplete finding |

누락 자체가 운영상 중요한 문제이면 `observability_gap` finding으로 기록한다.

## 14. 결론

Agent drift 탐지는 agent 내부 구조를 얼마나 관측할 수 있는지에 크게 의존한다. 따라서 Judge Agent는 특정 framework에 종속되지 않고 다음 전략을 취해야 한다.

1. 공통 Normalized Agent Run schema 정의
2. OTel GenAI를 기본 ingestion 표준으로 채택
3. framework별 adapter 제공
4. JSONL/manual instrumentation fallback 제공
5. trace 누락 자체를 observability drift로 평가
6. privacy/redaction을 기본 설계에 포함

이 접근을 따르면 LangChain/LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, LlamaIndex, PydanticAI, Semantic Kernel, Vercel AI SDK, Mastra, MCP/custom agent를 모두 Judge Agent 평가 파이프라인에 연결할 수 있다.
