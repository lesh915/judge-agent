# Simple Judge Agent MVP

`simple/judge_agent_simple` is the first executable MVP for the Simple Judge Agent.

It intentionally starts with the implemented reference agent integration:

```text
reference_agent/weblog_agent TraceLogger JSONL
  -> ReferenceAgentJsonlAdapter
  -> SimpleAgentRun
  -> ReferenceWebLogDetector
  -> AnalysisResult
  -> JudgeChatAgent session
  -> Markdown / JSON report or conversational drift analysis
```

## Run reference fixtures

macOS/Linux:

```bash
python3 -m reference_agent.weblog_agent.cli run-all \
  --no-llm \
  --output-dir artifacts/weblog-reference
```

Windows PowerShell:

```powershell
py -m reference_agent.weblog_agent.cli run-all `
  --no-llm `
  --output-dir artifacts/weblog-reference
```

## Analyze traces

macOS/Linux:

```bash
python3 -m simple.judge_agent_simple.cli analyze-batch \
  --traces 'artifacts/weblog-reference/*.jsonl' \
  --adapter reference-weblog-jsonl \
  --output artifacts/simple-judge/report.md \
  --json artifacts/simple-judge/findings.json \
  --fail-on high
```

Windows PowerShell:

```powershell
py -m simple.judge_agent_simple.cli analyze-batch `
  --traces "artifacts/weblog-reference/*.jsonl" `
  --adapter reference-weblog-jsonl `
  --output artifacts/simple-judge/report.md `
  --json artifacts/simple-judge/findings.json `
  --fail-on high
```

If installed as a package, the same CLI is available as:

```bash
judge-agent-simple analyze-batch --traces "artifacts/weblog-reference/*.jsonl"
```

## Conversational judge agent

The `chat` command starts an agent session over the detected findings. It keeps session state, classifies follow-up questions, selects relevant findings, and answers with evidence/recommendations instead of only printing a static report.

macOS/Linux:

```bash
python3 -m simple.judge_agent_simple.cli chat \
  --traces 'artifacts/weblog-reference/*.jsonl' \
  --session-id weblog-drift-review
```

Windows PowerShell:

```powershell
py -m simple.judge_agent_simple.cli chat `
  --traces "artifacts/weblog-reference/*.jsonl" `
  --session-id weblog-drift-review
```

Example questions:

- `왜 block이야?`
- `validation_path_coverage 근거 보여줘`
- `JD-001 수정 우선순위는?`
- `metric hallucination의 원인은?`

## Implemented checks

- `output_contract_compliance`
- `target_endpoint_consistency`
- `metric_result_consistency`
- `validation_path_coverage`
- `parse_error_handling_score`
- `rag_context_presence_and_usage`
- `mcp_context_presence_and_usage`
- `chat_context_grounding`

## Tests

```bash
python3 -m unittest discover -s simple/judge_agent_simple/tests
python3 -m unittest discover -s reference_agent/weblog_agent/tests
```
