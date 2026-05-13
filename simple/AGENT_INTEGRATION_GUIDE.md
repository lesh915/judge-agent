# Simple Agent Integration Guide: LangChain/LangGraph

## 1. 목적

이 문서는 LangChain/LangGraph agent에서 Judge Agent가 drift 탐지에 필요한 값을 어떻게 수집할지 정리한다.

초기 연동 방식은 3가지만 지원한다.

1. LangSmith trace export
2. LangChain callback JSONL
3. LangGraph custom event JSONL

## 2. 수집해야 하는 값

## 2.1 최소 필수 데이터

- run id
- user input
- final output
- LLM call input/output
- tool call name/arguments/result/error
- retriever query/results
- graph node start/end
- graph edge decision

## 2.2 권장 데이터

- system/developer instruction snapshot
- prompt template name/version
- available tool definitions
- LangGraph state before/after node
- checkpoint id
- approval/human interrupt event
- token usage/latency/cost

## 3. LangSmith 연동

## 3.1 방식

LangChain/LangGraph app에서 LangSmith tracing을 활성화하고 run export를 Judge Agent에 전달한다.

```text
LangChain/LangGraph Agent
  -> LangSmith trace
  -> LangSmith export/API
  -> Judge Agent LangSmithAdapter
  -> SimpleAgentRun
```

## 3.2 수집 가능한 정보

- run tree
- chain/llm/tool/retriever run
- input/output
- error
- latency
- token usage
- metadata/tags

## 3.3 권장 metadata

LangSmith run metadata에 다음을 추가한다.

```json
{
  "agent_name": "research-agent",
  "agent_version": "0.1.0",
  "prompt_version": "prompt-2026-05-13",
  "graph_version": "graph-0.3.0",
  "tool_policy_version": "tools-0.2.0"
}
```

## 3.4 Drift 탐지 포인트

- tool run이 user intent와 맞는가
- retriever run 결과와 final output이 일치하는가
- chain/graph run에서 error가 있었는가
- metadata version 변경 후 score가 하락했는가

## 4. LangChain Callback JSONL 연동

## 4.1 방식

LangChain callback handler를 만들어 주요 event를 JSONL로 기록한다.

```text
LangChain Agent
  -> CallbackHandler
  -> trace.jsonl
  -> Judge Agent JsonlAdapter
```

## 4.2 권장 Event

```jsonl
{"type":"run_start","run_id":"r1","user_input":"..."}
{"type":"llm_start","run_id":"r1","event_id":"e1","messages":[]}
{"type":"llm_end","run_id":"r1","event_id":"e1","output":"...","usage":{}}
{"type":"tool_start","run_id":"r1","event_id":"e2","tool":"search","arguments":{"query":"..."}}
{"type":"tool_end","run_id":"r1","event_id":"e2","output":{"results":[]}}
{"type":"retriever_end","run_id":"r1","event_id":"e3","query":"...","documents":[]}
{"type":"final_output","run_id":"r1","content":"..."}
```

## 4.3 구현 팁

- event마다 `run_id`와 `event_id`를 반드시 넣는다.
- tool start/end는 같은 `event_id`를 사용한다.
- error event를 별도로 기록한다.
- prompt raw text 저장이 부담되면 hash + summary + template version을 저장한다.

## 5. LangGraph Custom Event 연동

## 5.1 방식

LangGraph node 실행 전후에 state와 node transition을 기록한다.

```text
LangGraph Agent
  -> node wrapper / middleware
  -> graph-events.jsonl
  -> Judge Agent LangGraphAdapter
```

## 5.2 권장 Event

```jsonl
{"type":"graph_run_start","run_id":"r1","graph_version":"0.3.0"}
{"type":"node_start","run_id":"r1","event_id":"n1","node":"retrieve","state_before":{"query":"..."}}
{"type":"node_end","run_id":"r1","event_id":"n1","node":"retrieve","state_after":{"docs":["d1"]}}
{"type":"edge_selected","run_id":"r1","from":"retrieve","to":"answer","reason":"docs_found"}
{"type":"checkpoint_saved","run_id":"r1","checkpoint_id":"c1","node":"retrieve"}
{"type":"final_output","run_id":"r1","content":"..."}
```

## 5.3 Drift 탐지 포인트

- required node가 실행되었는가
- conditional edge reason이 state와 맞는가
- 같은 node를 반복하지 않았는가
- approval/validation node를 건너뛰지 않았는가
- state_after가 다음 node input과 일치하는가

## 6. LangGraph State 수집 권장안

state 전체를 저장하면 민감정보가 포함될 수 있으므로 다음 원칙을 따른다.

- 기본은 redacted state 저장
- 중요한 field만 allowlist
- 큰 document content는 source id와 score만 저장
- 필요 시 context chunk text는 별도 redaction 후 저장

권장 allowlist:

```json
[
  "task_id",
  "user_intent",
  "selected_tool",
  "retrieved_doc_ids",
  "validation_status",
  "approval_status",
  "error_code",
  "final_status"
]
```

## 7. Tool Call 수집 규칙

tool drift를 탐지하려면 다음이 필요하다.

```json
{
  "tool_name": "string",
  "arguments": {},
  "result": {},
  "error": null,
  "schema_version": "string",
  "source_event_ids": []
}
```

`source_event_ids`는 argument 값이 어떤 context/state/message에서 왔는지 연결하기 위한 필드다.

## 8. Retriever 수집 규칙

context drift를 탐지하려면 retriever 결과를 다음처럼 저장한다.

```json
{
  "query": "string",
  "documents": [
    {
      "id": "doc-1",
      "score": 0.82,
      "source": "kb/article.md",
      "text": "redacted or excerpt"
    }
  ]
}
```

## 9. Integration Checklist

### 필수

- [ ] run_id
- [ ] user input
- [ ] final output
- [ ] LLM calls
- [ ] tool calls/results/errors
- [ ] retriever results if RAG 사용

### LangGraph 사용 시 필수

- [ ] node start/end
- [ ] selected edge
- [ ] state before/after 핵심 필드
- [ ] checkpoint id

### 권장

- [ ] instruction snapshot
- [ ] prompt version
- [ ] tool schema version
- [ ] graph version
- [ ] approval/interrupt events
- [ ] error/retry events

## 10. 우선순위

MVP에서는 LangSmith trace export를 1순위로 지원한다.

그 다음 순서:

1. LangSmithAdapter
2. LangChain JSONL Adapter
3. LangGraph JSONL Adapter
4. Generic OTel GenAI Adapter
