# Drift 탐지용 데이터 전송/수집 코드 가이드

작성일: 2026-05-14

이 문서는 `reference_agent/weblog_agent`가 **drift 현상 탐지를 위해 어떤 데이터를 어디서 생성하고, 어떤 코드 경로로 전송/기록하는지**를 정리한다. 향후 다른 에이전트에 drift 탐지 기능을 붙일 때는 이 문서의 "필수 이식 포인트"를 기준으로 구현하면 된다.

> 현재 reference agent의 "전송"은 네트워크 전송이 아니라 **JSONL trace 파일로 내보내는 telemetry sink**이다. 운영 환경에서는 `TraceLogger.emit()` 부분을 HTTP/event bus/observability collector로 교체하거나 이중화하면 된다.

---

## 1. 전체 구조 요약

```text
CLI/API entrypoint
  -> TraceLogger 생성
  -> Agent에 TraceLogger 주입
  -> Agent 실행 중 주요 이벤트 emit
      - run/session lifecycle
      - prompt/instruction snapshot
      - graph node transition
      - ReAct thought/action/observation
      - tool call input/output/error
      - LLM request/response/error/skipped
      - MCP request/response/error
      - RAG retrieval result
      - validation result
      - final output
  -> JSONL trace 파일 저장
  -> Judge Agent가 trace를 읽어 drift 탐지
```

핵심은 모든 drift 관측 데이터가 `TraceLogger`를 통과한다는 점이다.

---

## 2. Drift telemetry의 단일 sink: `TraceLogger`

파일: `reference_agent/weblog_agent/trace.py`

| 코드 | 역할 | 다른 에이전트 이식 시 필수 여부 |
|---|---|---|
| `TraceLogger.__init__()` | run/session 단위 trace 파일과 `run_id` 생성 | 필수 |
| `TraceLogger.emit()` | 모든 telemetry event를 JSONL 한 줄로 기록 | 필수 |
| `redact()` | token, api_key, password, secret 문자열 마스킹 | 필수 |
| `node_start()` / `node_end()` | graph node 실행 전후 state snapshot 기록 | 권장 |
| `tool_start()` / `tool_end()` / `tool_error()` | tool 호출 전후 및 실패 기록 | 필수 |

현재 구현 위치:

```python
# trace.py
class TraceLogger:
    def emit(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        event = {
            "type": event_type,
            "run_id": self.run_id,
            "timestamp": ...,
            **payload,
        }
        event = redact(event)
        self._fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
```

다른 에이전트에 붙일 때는 최소한 다음 인터페이스를 유지한다.

```python
trace.emit("event_type", key=value, ...)
trace.tool_start("tool_name", arguments)
trace.tool_end(event_id, "tool_name", output)
trace.tool_error(event_id, "tool_name", error)
```

운영 환경에서 collector로 보낼 경우:

```python
def emit(self, event_type, **payload):
    event = build_event(...)
    event = redact(event)
    write_jsonl(event)          # 로컬 재현성
    post_to_collector(event)    # 중앙 drift 탐지 시스템
```

---

## 3. Entry point에서 trace를 생성하는 위치

파일: `reference_agent/weblog_agent/cli.py`

| 함수 | 코드 역할 | 생성되는 trace |
|---|---|---|
| `run_fixture()` | fixture 기반 drift/normal 시나리오 실행 | `{fixture_id}.jsonl` |
| `run_all()` | 모든 fixture 반복 실행 | fixture별 JSONL |
| `run_analysis()` | 사용자 정의 단발 분석 실행 | `custom-run.jsonl` 또는 지정 경로 |
| `run_chat()` | 대화형 세션 trace 생성 | `{session_id}-chat.jsonl` |

핵심 코드 흐름:

```python
logger = TraceLogger(trace_path, run_id=fixture_id)
agent = WebLogAnalysisAgent(logger, fault=fx.fault, use_llm=use_llm)
state = agent.run(...)
```

즉, **다른 에이전트도 실행 시작 지점에서 TraceLogger를 만들고 Agent 객체에 주입**해야 한다.

권장 패턴:

```python
def run_my_agent(user_input, ...):
    trace = TraceLogger(trace_path, run_id=run_id)
    try:
        agent = MyAgent(trace_logger=trace)
        return agent.run(user_input)
    finally:
        trace.close()
```

---

## 4. 단발 ReAct Agent의 drift telemetry 위치

파일: `reference_agent/weblog_agent/graph.py`

`WebLogAnalysisAgent`는 실제 drift 탐지용 데이터를 가장 많이 생성하는 부분이다.

### 4.1 Run lifecycle

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `run_start` | `WebLogAnalysisAgent.run()` 시작 | 에이전트 버전, 프레임워크, architecture, component, LLM 설정 기록 |
| `run_end` | `run()` 종료 | 성공/오류 상태 기록 |
| `final_output` | `run()` 종료 직전 | 최종 응답/리포트 기록 |

`run_start`는 다른 에이전트에서 반드시 남기는 것이 좋다. Judge Agent가 "어떤 agent/version/prompt/toolset에서 drift가 발생했는지"를 묶어 볼 수 있기 때문이다.

필수 payload 예:

```json
{
  "type": "run_start",
  "agent_name": "...",
  "agent_version": "...",
  "framework": "langgraph|custom|...",
  "architecture": "react|planner|workflow|chat",
  "components": ["llm", "prompt", "tools", "rag", "mcp"],
  "user_input": "...",
  "llm_model": "...",
  "llm_config": {"sanitized": true}
}
```

### 4.2 Prompt / instruction snapshot

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `instruction_snapshot` | `run()` 초반 | system prompt, ReAct protocol, tool policy, output contract 기록 |

이 이벤트는 prompt drift 탐지에 매우 중요하다.

탐지 가능한 문제:

- system prompt 변경으로 인한 응답 품질 변화
- output contract 누락
- tool policy 변경
- instruction conflict
- prompt가 길어지며 핵심 규칙이 희석되는 문제

다른 에이전트에서도 최소한 다음을 남긴다.

```python
trace.emit(
    "instruction_snapshot",
    system=SYSTEM_PROMPT,
    tool_policy=TOOL_POLICY,
    output_contract=OUTPUT_CONTRACT,
)
```

보안상 전체 prompt를 보낼 수 없다면 `prompt_hash`, `prompt_version`, `policy_ids`라도 남긴다.

### 4.3 Graph node / edge telemetry

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `edge_selected` | `_edge()` | 어떤 node에서 어떤 node로 왜 이동했는지 기록 |
| `node_start` | `_node()` | node 실행 전 state snapshot 기록 |
| `node_end` | `_node()` | node 실행 후 state snapshot 기록 |

관련 코드:

```python
def _node(self, name, state, fn):
    eid = self.trace.node_start(name, state.snapshot())
    fn(state)
    self.trace.node_end(eid, name, state.snapshot())
```

이 데이터로 탐지 가능한 drift:

- 원래 거쳐야 하는 validation node를 건너뜀
- 특정 node 반복/누락
- state가 예상과 다르게 변함
- graph routing이 잘못됨

### 4.4 ReAct loop telemetry

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `react_step` | `react_agent()` | step별 thought, action, action_input 기록 |
| `observation` | `react_agent()` | tool 실행 결과 요약 기록 |

이 데이터로 탐지 가능한 drift:

- 잘못된 tool 선택
- 같은 tool 반복 호출
- action_input이 사용자 요청과 불일치
- observation을 무시하고 다음 행동 수행
- ReAct loop가 `max_steps`를 초과

다른 에이전트에서도 planner/action loop가 있다면 이와 같은 이벤트를 남긴다.

```python
trace.emit("react_step", step=i, thought=thought, action=tool_name, action_input=args)
trace.emit("observation", step=i, action=tool_name, observation=summarized_output)
```

주의: observation에는 raw data 전체가 아니라 요약본을 넣는 것이 좋다.

### 4.5 Tool telemetry

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `tool_start` | `_tool()` | tool 이름과 입력 인자 기록 |
| `tool_end` | `_tool()` | tool 출력 기록 |
| `tool_error` | `_tool()` | 예외 타입/메시지 기록 |

관련 코드:

```python
def _tool(self, name, fn, args):
    eid = self.trace.tool_start(name, args)
    try:
        out = fn(**args)
        redacted = {k: v for k, v in out.items() if k not in {"lines", "records"}}
        self.trace.tool_end(eid, name, redacted)
        return out
    except Exception as exc:
        self.trace.tool_error(eid, name, {"message": str(exc), "type": exc.__class__.__name__})
        raise
```

중요 포인트:

- `lines`, `records` 같은 대용량/민감 raw data는 `tool_end`에서 제외한다.
- 하지만 `line_count`, `matched_count`, `request_count`, `error_rate` 같은 drift 판단용 summary는 남긴다.

탐지 가능한 drift:

- wrong endpoint: `filter_log_records` 입력의 `path_pattern`이 사용자 요청과 불일치
- metric hallucination: `compute_log_metrics` 결과와 최종 응답이 불일치
- parse error ignored: `parse_error_count`가 높은데 validation/report에서 무시
- tool call schema 오류
- tool failure 후 회복 실패

### 4.6 LLM telemetry

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `llm_start` | `_llm_call()` | 모델명과 messages 기록 |
| `llm_end` | `_llm_call()` | 모델 output, usage, latency 기록 |
| `llm_error` | `_llm_call()` | LLM 호출 실패 기록 |
| `llm_skipped` | `_llm_call()` | `--no-llm` 또는 API key 미설정 기록 |

이 데이터로 탐지 가능한 drift:

- 같은 prompt에서 다른 output 경향
- output contract 위반
- LLM latency/cost 급증
- fallback policy 사용 여부
- prompt bloat로 messages 크기 증가

보안 주의:

- 현재 trace는 `redact()`를 통과하지만, 운영에서는 message 본문 전체를 보내기 어렵다면 `message_hash`, `token_count`, `prompt_version`, `selected_memory_ids`를 보내는 방식으로 축약한다.

### 4.7 MCP telemetry

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `mcp_start` | `_mcp_list_tools()`, `_mcp_call()` | MCP method/tool/arguments 기록 |
| `mcp_end` | `_mcp_list_tools()`, `_mcp_call()` | MCP output 기록 |
| `mcp_error` | `_mcp_list_tools()`, `_mcp_call()` | MCP 실패 기록 |

이 데이터로 탐지 가능한 drift:

- MCP tool list 변경
- 서비스 owner/SLO/dependency context 누락
- 잘못된 MCP tool 호출
- service metadata를 최종 응답에서 무시

### 4.8 RAG telemetry

RAG는 별도 `rag_start` 이벤트가 아니라 tool wrapper를 통해 기록된다.

| tool | 코드 위치 | 기록 이벤트 |
|---|---|---|
| `retrieve_runbook` | `_execute_action()` | `tool_start` / `tool_end` |

`tool_end` output에 `documents`, `doc_id`, `score`, `source`, `content`가 포함된다.

탐지 가능한 drift:

- RAG context missing
- 관련 없는 runbook 검색
- runbook 근거를 최종 답변에서 누락
- RAG 문서를 과신하거나 hallucination과 섞음

### 4.9 Validation telemetry

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `validation_result` | `validate_findings()`, `finalize()` | 검증 통과 여부와 issue 목록 기록 |

관련 검증 로직:

파일: `reference_agent/weblog_agent/validation.py`

검증 항목:

- metrics 존재 여부
- anomaly가 있는데 log evidence가 있는지
- RAG context 존재 여부
- MCP context 존재 여부
- truncated log limitation이 최종 report에 반영되었는지
- 최종 report 필수 section 존재 여부

탐지 가능한 drift:

- validation skipped
- output contract 위반
- evidence 없는 anomaly 주장
- RAG/MCP context 누락
- limitation 누락

---

## 5. 대화형 Agent의 drift telemetry 위치

파일: `reference_agent/weblog_agent/chat_agent.py`

대화형 모드에서는 단발 분석 trace와 별도로 chat session trace가 생긴다.

| 이벤트 | 코드 위치 | 목적 |
|---|---|---|
| `chat_session_start` | `ChatAgent.start()` | session id, access log, 기존 turn 수, LLM 설정 기록 |
| `chat_session_end` | `ChatAgent.end()` | session 종료와 turn count 기록 |
| `chat_turn_start` | `handle_user_turn()` | 사용자 입력 turn 기록 |
| `chat_intent_classified` | `handle_user_turn()` | `new_analysis`, `followup`, `clarification` 분류 결과 기록 |
| `chat_analysis_invoked` | `_run_analysis_turn()` | child ReAct trace/report 경로 기록 |
| `chat_context_built` | `build_chat_context()` | 후속 답변에 사용한 context 구성 정보 기록 |
| `chat_response_generated` | `handle_user_turn()` | 최종 assistant 응답 기록 |
| `chat_turn_end` | `handle_user_turn()` | turn 종료 기록 |

대화형 drift에서 중요한 지점:

1. **intent drift**: 새 분석 요청을 follow-up으로 잘못 분류하거나 반대의 경우
2. **context drift**: 이전 분석과 무관한 context로 답변
3. **memory pollution**: 오래된 session state가 새 답변에 섞임
4. **follow-up hallucination**: `last_analysis`에 없는 metric/cause를 주장

다른 대화형 에이전트도 최소한 아래 이벤트를 남긴다.

```python
trace.emit("chat_turn_start", session_id=..., turn=..., user_input=...)
trace.emit("chat_intent_classified", session_id=..., turn=..., intent=...)
trace.emit("chat_context_built", session_id=..., context_ids=[...], has_last_result=True)
trace.emit("chat_response_generated", session_id=..., turn=..., response=...)
```

---

## 6. Drift 시나리오 fixture 위치

파일: `reference_agent/weblog_agent/fixtures.py`

현재 fixture는 정상/드리프트 상황을 인위적으로 재현하기 위한 데이터셋이다.

| fixture id | fault | expected_category | 탐지 의도 |
|---|---|---|---|
| `normal-login-error-spike` | 없음 | 없음 | 정상 기준 trace |
| `drift-prompt-output-contract` | `prompt_output_contract` | `prompt` | output contract 위반 |
| `drift-wrong-endpoint` | `wrong_endpoint` | `tool` | 사용자 요청과 다른 endpoint 분석 |
| `drift-parse-error-ignored` | `parse_error_ignored` | `tool` | parse error 무시 |
| `drift-validation-skipped` | `validation_skipped` | `graph` | validation node 우회 |
| `drift-metric-hallucination` | `metric_hallucination` | `completion` | 계산값과 다른 metric 주장 |

fault injection 실제 위치는 `graph.py`의 `_execute_action()`, `run()`, `_generate_final_report()` 주변이다.

---

## 7. State snapshot에 포함되는 drift 판단 데이터

파일: `reference_agent/weblog_agent/state.py`

`WebLogAnalysisState.snapshot()`은 `node_start` / `node_end`에 들어가는 핵심 상태 요약이다.

포함 필드:

- `request`: raw user input, targetPath, requestedMetrics, statusFocus
- `logSource`: access log path, format
- `rawLogs`: lineCount, truncated
- `parsedRecordCount`
- `filteredRecordCount`
- `metrics`
- `baseline`
- `anomalies`
- `evidence`
- `ragContextCount`
- `mcpContext`
- `reactStepCount`
- `validation`
- `errors`
- `finalReportPresent`

중요한 설계 의도:

- raw log 전체는 snapshot에 넣지 않는다.
- drift 판단에 필요한 count/metric/context 여부를 남긴다.
- tool output에서 raw records는 제외하고, 필요한 경우 대표 evidence만 보존한다.

다른 에이전트도 state snapshot을 만들 때 다음 원칙을 따른다.

```text
원본 대용량 데이터 X
판단 가능한 요약값 O
사용자 의도 O
선택된 도구/입력 O
검증 결과 O
최종 출력 존재 여부 O
```

---

## 8. 이벤트별 drift 탐지 활용 매핑

| Drift 유형 | 필요한 이벤트 | 보는 필드 |
|---|---|---|
| Prompt drift | `instruction_snapshot`, `llm_start`, `final_output`, `validation_result` | prompt 내용/버전, output contract, missing section |
| Tool selection drift | `react_step`, `tool_start`, `tool_end`, `observation` | action, action_input, tool output summary |
| Wrong endpoint drift | `request`, `tool_start(filter_log_records)`, `metrics.top_paths` | targetPath vs path_pattern/top_paths |
| Metric hallucination | `tool_end(compute_log_metrics)`, `final_output`, `validation_result` | computed metrics vs report claims |
| Validation skipped | `edge_selected`, `node_start`, `validation_result` | validate node 통과 여부 |
| RAG context drift | `tool_end(retrieve_runbook)`, `validation_result`, `final_output` | documents/source/score, report 근거 반영 |
| MCP context drift | `mcp_start`, `mcp_end`, `validation_result`, `final_output` | owner/SLO/dependencies 반영 여부 |
| Context bloat | `llm_start`, `chat_context_built`, `state.snapshot` | messages 크기, recent_turn_count, summary_count |
| Conversation drift | `chat_intent_classified`, `chat_context_built`, `chat_response_generated` | intent, selected context, response |

---

## 9. 다른 에이전트에 붙일 때의 필수 이식 포인트

### 9.1 최소 필수 코드

```python
trace = TraceLogger(trace_path, run_id=run_id)
trace.emit("run_start", agent_name=..., agent_version=..., user_input=...)
trace.emit("instruction_snapshot", system=..., tool_policy=..., output_contract=...)

# LLM call
trace.emit("llm_start", name="...", model=model, messages=messages)
result = llm.chat(messages)
trace.emit("llm_end", name="...", model=model, output=result.text, usage=result.usage)

# Tool call
eid = trace.tool_start("tool_name", args)
out = tool(**args)
trace.tool_end(eid, "tool_name", summarize(out))

# Final
trace.emit("validation_result", passed=..., issues=[...])
trace.emit("final_output", content=answer)
trace.emit("run_end", status="completed")
```

### 9.2 ReAct/graph agent라면 추가

```python
trace.emit("edge_selected", from="plan", to="tool", reason="...")
node_id = trace.node_start("node_name", state.snapshot())
...
trace.node_end(node_id, "node_name", state.snapshot())
trace.emit("react_step", step=i, thought=thought, action=action, action_input=args)
trace.emit("observation", step=i, action=action, observation=summarize(out))
```

### 9.3 대화형 agent라면 추가

```python
trace.emit("chat_session_start", session_id=..., turn_count=...)
trace.emit("chat_turn_start", session_id=..., turn=..., user_input=...)
trace.emit("chat_intent_classified", session_id=..., turn=..., intent=...)
trace.emit("chat_context_built", session_id=..., context_ids=..., recent_turn_count=...)
trace.emit("chat_response_generated", session_id=..., turn=..., response=...)
trace.emit("chat_turn_end", session_id=..., turn=...)
```

---

## 10. Privacy / 보안 주의사항

현재 reference agent는 fixture 기반이라 raw log 일부가 trace에 들어갈 수 있다. 운영 에이전트에 적용할 때는 다음을 지켜야 한다.

1. secret redaction은 필수이다.
2. raw document/log/message 전체 대신 summary, count, hash, id를 우선 전송한다.
3. LLM message 전문을 보내기 어렵다면 prompt hash/version/token count를 보낸다.
4. tool arguments에 개인정보가 들어갈 수 있으면 allowlist 기반으로 필드만 남긴다.
5. trace collector 전송 실패가 agent 실행 실패로 이어지지 않게 best-effort queue를 둔다.
6. 사용자별/session별 삭제 요청을 처리할 수 있게 `run_id`, `session_id`를 남긴다.

---

## 11. 권장 collector payload 스키마

현재 JSONL event의 공통 필드는 다음과 같다.

```json
{
  "type": "tool_end",
  "run_id": "normal-login-error-spike",
  "timestamp": "2026-05-13T05:47:46Z",
  "event_id": "tool-compute_log_metrics-0f0d0a",
  "tool": "compute_log_metrics",
  "output": {
    "request_count": 80,
    "error_rate": 0.15
  }
}
```

운영 collector로 보낼 때도 최소 공통 필드를 유지한다.

| 필드 | 설명 |
|---|---|
| `type` | 이벤트 타입 |
| `run_id` | 단일 실행 식별자 |
| `session_id` | 대화형이면 세션 식별자 |
| `timestamp` | UTC timestamp |
| `agent_name` | agent 이름 |
| `agent_version` | agent 버전 |
| `event_id` | node/tool/llm event 식별자 |
| `payload` | 이벤트별 데이터 |

---

## 12. 한 줄 결론

다른 에이전트에 drift 탐지를 붙일 때 설명해야 할 핵심은 다음이다.

> **Agent 실행 entrypoint에서 `TraceLogger`를 만들고, LLM/Tool/RAG/MCP/Graph/Validation/Final output의 모든 핵심 순간에 `trace.emit()` 또는 `trace.tool_*()`를 호출하는 부분이 drift 탐지용 데이터 전송 코드이다.**

이 reference agent에서는 그 중심이 `trace.py`의 `TraceLogger.emit()`이고, 실제 호출 지점은 `cli.py`, `graph.py`, `chat_agent.py`에 분산되어 있다.
