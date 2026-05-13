# Web Log Analysis Reference Agent

Runnable web-log analysis agent for Judge Agent drift development.

This is no longer just a static test harness. It runs a real agent pipeline:

1. parses the user's log-analysis intent, using an OpenAI-compatible LLM when configured;
2. executes log-analysis tools;
3. moves through LangGraph-compatible node/edge workflow events;
4. validates evidence and metrics;
5. generates the final markdown report, using the LLM when available and a deterministic fallback when not;
6. emits JSONL trace events for Judge Agent drift evaluation.

The implementation is dependency-light so it can run in CI without external packages, but it exposes the same trace contract expected from a LangGraph implementation. A later iteration can swap the sequential runner for the actual LangGraph runtime without changing Judge Agent inputs.

## LLM configuration

The agent uses an OpenAI-compatible Chat Completions endpoint via Python standard library HTTP calls.

Environment variables:

```bash
export OPENAI_API_KEY=...
export WEBLOG_AGENT_MODEL=gpt-4o-mini          # optional
export OPENAI_BASE_URL=https://api.openai.com/v1 # optional, OpenAI-compatible endpoint
```

If no API key is configured, the agent still works with deterministic fallback logic and emits `llm_skipped` events in the trace. For deterministic CI runs, pass `--no-llm`.

## Run

```bash
python3 -m reference_agent.weblog_agent.cli list-fixtures
python3 -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike
python3 -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike --no-llm
python3 -m reference_agent.weblog_agent.cli run-all --no-llm
```

Run a custom analysis:

```bash
python3 -m reference_agent.weblog_agent.cli analyze   --input "지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요"   --access-log reference_agent/weblog_agent/fixtures/access.log
```

Outputs are written to:

- `reference_agent/weblog_agent/traces/*.jsonl`
- `reference_agent/weblog_agent/reports/*.md`

## Trace events

The agent emits:

- `run_start` / `run_end`
- `instruction_snapshot`
- `llm_start` / `llm_end` / `llm_error` / `llm_skipped`
- `node_start` / `node_end`
- `edge_selected`
- `tool_start` / `tool_end` / `tool_error`
- `validation_result`
- `final_output`
