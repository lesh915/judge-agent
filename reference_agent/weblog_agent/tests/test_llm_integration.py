from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reference_agent.weblog_agent.fixtures import FIXTURE_DIR
from reference_agent.weblog_agent.graph import WebLogAnalysisAgent
from reference_agent.weblog_agent.llm import LLMConfig
from reference_agent.weblog_agent.trace import TraceLogger


class FakeLLM:
    def __init__(self):
        self.config = LLMConfig(model="fake-chat-model")
        self.calls = []

    @property
    def enabled(self):
        return True

    def chat(self, messages, response_format=None):
        self.calls.append({"messages": messages, "response_format": response_format})
        if response_format:
            return {
                "id": "fake-parse",
                "model": "fake-chat-model",
                "content": json.dumps({
                    "targetPath": "/api/login",
                    "requestedMetrics": ["error_rate", "latency"],
                    "statusMin": 0,
                    "statusMax": 599,
                    "statusFocus": "5xx",
                }),
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                "latency_ms": 1,
            }
        return {
            "id": "fake-report",
            "model": "fake-chat-model",
            "content": "\n".join([
                "## Summary",
                "Analyzed `/api/login` with evidence-backed metrics.",
                "## Key Metrics",
                "- request_count: 80",
                "- error_rate: 15.00%",
                "## Anomalies",
                "- error_rate_spike and latency_spike detected.",
                "## Evidence",
                "- Evidence comes from parsed access-log records and computed metrics.",
                "## Recommended Actions",
                "- Inspect recent `/api/login` deploys and upstream dependencies.",
                "## Confidence & Limitations",
                "- Confidence: medium; based on fixture access logs only.",
            ]),
            "usage": {"prompt_tokens": 50, "completion_tokens": 100},
            "latency_ms": 1,
        }


class LLMIntegrationTests(unittest.TestCase):
    def test_agent_emits_llm_events_when_llm_is_enabled(self):
        with tempfile.TemporaryDirectory() as td:
            trace_path = Path(td) / "trace.jsonl"
            logger = TraceLogger(trace_path, run_id="llm-test")
            try:
                fake_llm = FakeLLM()
                agent = WebLogAnalysisAgent(logger, llm=fake_llm, use_llm=True)
                state = agent.run(
                    "지난 1시간 동안 /api/login 5xx 에러율과 latency를 분석해주세요",
                    str(FIXTURE_DIR / "access.log"),
                )
            finally:
                logger.close()

            self.assertEqual(len(fake_llm.calls), 2)
            self.assertIn("## Summary", state.finalReport)
            events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            event_types = [event["type"] for event in events]
            self.assertIn("llm_start", event_types)
            self.assertIn("llm_end", event_types)
            self.assertNotIn("llm_skipped", event_types)
            self.assertTrue(any(event.get("name") == "parse_request" and event["type"] == "llm_end" for event in events))
            self.assertTrue(any(event.get("name") == "generate_report" and event["type"] == "llm_end" for event in events))


if __name__ == "__main__":
    unittest.main()
