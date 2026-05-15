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

Three modes are available:

- `--mode deterministic` — legacy keyword-based conversational layer over analyzed findings.
- `--mode deterministic-v2` — tool-based conversational runtime. It uses a metric registry from `docs/DRIFT_METRICS.xlsx`, records tool calls/evidence in conversation state, preserves focused metric/finding context, and can answer follow-up questions such as “그 근거는?” or “수정 우선순위는?”.
- `--mode hybrid` — deterministic tools + optional LLM response synthesis. The LLM does not decide drift by itself; it only rewrites/explains grounded tool results. If no provider is configured, it falls back to deterministic-v2 output.

macOS/Linux:

```bash
python3 -m simple.judge_agent_simple.cli chat \
  --mode deterministic-v2 \
  --traces 'artifacts/weblog-reference/*.jsonl' \
  --session-id weblog-drift-review
```

Windows PowerShell:

```powershell
py -m simple.judge_agent_simple.cli chat `
  --mode deterministic-v2 `
  --traces "artifacts/weblog-reference/*.jsonl" `
  --session-id weblog-drift-review
```

Hybrid mode with OpenAI-compatible configuration:

```bash
OPENAI_API_KEY=... python3 -m simple.judge_agent_simple.cli chat \
  --mode hybrid \
  --llm-provider openai \
  --llm-model gpt-4o-mini \
  --traces 'artifacts/weblog-reference/*.jsonl' \
  --session-id weblog-drift-review
```

For tests and local dry-runs without external calls:

```bash
python3 -m simple.judge_agent_simple.cli chat \
  --mode hybrid \
  --llm-provider mock \
  --traces 'artifacts/weblog-reference/*.jsonl'
```

Example questions:

- `왜 block이야?`
- `validation_path_coverage 근거 보여줘`
- `JD-001 수정 우선순위는?`
- `metric hallucination의 원인은?`
- `MVP 우선순위 기준으로 먼저 고칠 것 알려줘`
- `그 근거는?`
- `run 비교`

## Metric registry

`judge_agent_simple.metrics` contains the first implementation of the drift metric registry based on `docs/DRIFT_METRICS.xlsx`.

Covered priority groups:

- MVP metrics: `tool_argument_correctness`, `tool_error_handling_score`, `answer_context_groundedness`, `node_sequence_correctness`, `verification_coverage`, `instruction_adherence_score`, `redundant_tool_call_count`
- Reference agent metrics: `output_contract_compliance`, `target_endpoint_consistency`, `metric_result_consistency`, `validation_path_coverage`, `parse_error_handling_score`, `rag_context_presence_and_usage`, `mcp_context_presence_and_usage`, `chat_context_grounding`

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
