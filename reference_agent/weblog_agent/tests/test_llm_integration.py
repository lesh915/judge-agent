from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reference_agent.weblog_agent.fixtures import FIXTURE_DIR
from reference_agent.weblog_agent.graph import WebLogAnalysisAgent
from reference_agent.weblog_agent.llm import LLMConfig
from reference_agent.weblog_agent.trace import TraceLogger


class FakeReActLLM:
    def __init__(self):
        self.config = LLMConfig(model="fake-react-model")
        self.calls = []
        self.actions = iter([
            {"thought": "Parse user intent first.", "action": "parse_user_request", "action_input": {"text": "지난 1시간 동안 /api/login 5xx 에러율과 latency를 분석해주세요"}},
            {"thought": "Load access logs.", "action": "read_log_file", "action_input": {}},
            {"thought": "Parse raw logs.", "action": "parse_access_log", "action_input": {}},
            {"thought": "Scope records to requested endpoint.", "action": "filter_log_records", "action_input": {}},
            {"thought": "Compute metrics from scoped records.", "action": "compute_log_metrics", "action_input": {}},
            {"thought": "Detect abnormal metrics.", "action": "detect_log_anomalies", "action_input": {}},
            {"thought": "Retrieve runbook context.", "action": "retrieve_runbook", "action_input": {"query": "/api/login"}},
            {"thought": "Fetch service metadata through MCP.", "action": "get_service_context", "action_input": {"path": "/api/login"}},
            {"thought": "Collect evidence lines.", "action": "collect_evidence", "action_input": {}},
            {"thought": "All observations are ready.", "action": "finish", "final": "\n".join([
                "## Summary",
                "Analyzed `/api/login` with ReAct, tools, RAG, and MCP.",
                "## Key Metrics",
                "- request_count: 80",
                "- error_rate: 15.00%",
                "## Anomalies",
                "- error_rate_spike and latency_spike detected.",
                "## Evidence",
                "- Evidence comes from parsed access-log records and computed metrics.",
                "## RAG Context",
                "- Runbook retrieved for /api/login.",
                "## MCP Context",
                "- Service metadata fetched through MCP.",
                "## Recommended Actions",
                "- Inspect recent `/api/login` deploys and upstream dependencies.",
                "## Confidence & Limitations",
                "- Confidence: medium; based on fixture access logs only.",
            ])},
        ])

    @property
    def enabled(self):
        return True

    def chat(self, messages, response_format=None):
        self.calls.append({"messages": messages, "response_format": response_format})
        return {
            "id": "fake-react",
            "model": "fake-react-model",
            "content": json.dumps(next(self.actions), ensure_ascii=False),
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "latency_ms": 1,
        }


class LLMIntegrationTests(unittest.TestCase):
    def test_agent_emits_llm_and_react_events_when_llm_is_enabled(self):
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            logger = TraceLogger(trace_path, run_id="react-llm-test")
            try:
                fake_llm = FakeReActLLM()
                agent = WebLogAnalysisAgent(logger, llm=fake_llm, use_llm=True)
                state = agent.run(
                    "지난 1시간 동안 /api/login 5xx 에러율과 latency를 분석해주세요",
                    str(FIXTURE_DIR / "access.log"),
                )
            finally:
                logger.close()

            self.assertEqual(len(fake_llm.calls), 10)
            self.assertIn("## RAG Context", state.finalReport)
            self.assertIn("## MCP Context", state.finalReport)
            self.assertTrue(state.ragContext)
            self.assertTrue(state.mcpContext)
            events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            event_types = [event["type"] for event in events]
            self.assertIn("llm_start", event_types)
            self.assertIn("llm_end", event_types)
            self.assertIn("react_step", event_types)
            self.assertIn("mcp_start", event_types)
            self.assertIn("mcp_end", event_types)
            self.assertNotIn("llm_skipped", event_types)
            self.assertTrue(any(event.get("name") == "react_decide" and event["type"] == "llm_end" for event in events))


if __name__ == "__main__":
    unittest.main()
