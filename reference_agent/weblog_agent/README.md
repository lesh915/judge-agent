# Web Log Analysis Reference Agent

Runnable test/reference agent for Judge Agent drift development.

## Run

```bash
python3 -m reference_agent.weblog_agent.cli list-fixtures
python3 -m reference_agent.weblog_agent.cli run-fixture normal-login-error-spike
python3 -m reference_agent.weblog_agent.cli run-all
```

Outputs are written to:

- `reference_agent/weblog_agent/traces/*.jsonl`
- `reference_agent/weblog_agent/reports/*.md`

The implementation is dependency-light and emits LangGraph-compatible node/edge/tool traces so it can run in test environments without installing external packages. A future iteration can swap the internal sequential runner for the actual LangGraph runtime without changing the trace contract.
