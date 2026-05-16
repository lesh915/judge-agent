from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from simple.judge_agent_simple.conversation.agent import ToolBasedConversationAgent
from simple.judge_agent_simple.conversation.state import ConversationState, load_conversation_state
from simple.judge_agent_simple.core.metrics import get_metric, validate_metric_coverage
from simple.judge_agent_simple.analysis.tools import load_traces, summarize_findings


class ConversationAgentTests(unittest.TestCase):
    def _run_fixture(self, fixture_id: str, output_dir: Path) -> Path:
        proc = subprocess.run([
            sys.executable, "-m", "reference_agent.weblog_agent.cli", "run-fixture", fixture_id,
            "--output-dir", str(output_dir), "--no-llm",
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(json.loads(proc.stdout)["trace_path"])

    def test_metric_registry_covers_mvp_and_reference_metrics(self):
        required = [
            "tool_argument_correctness",
            "tool_error_handling_score",
            "answer_context_groundedness",
            "node_sequence_correctness",
            "verification_coverage",
            "instruction_adherence_score",
            "redundant_tool_call_count",
            "output_contract_compliance",
            "target_endpoint_consistency",
            "metric_result_consistency",
            "validation_path_coverage",
            "parse_error_handling_score",
            "rag_context_presence_and_usage",
            "mcp_context_presence_and_usage",
            "chat_context_grounding",
        ]
        self.assertEqual(validate_metric_coverage(required), [])
        self.assertEqual(get_metric("tool_argument_correctness").mvp_priority, 1)
        self.assertEqual(get_metric("validation_path_coverage").ref_agent_priority, 4)

    def test_tool_registry_loads_and_summarizes_metric_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture("drift-validation-skipped", Path(td) / "fixtures")
            state = ConversationState(session_id="tool-test")
            loaded = load_traces(state, [str(trace)])
            self.assertEqual(loaded["run_count"], 1)
            summary = summarize_findings(state)
            metrics = [finding["metric"] for finding in summary["top_findings"]]
            self.assertIn("validation_path_coverage", metrics)
            first = summary["top_findings"][0]
            self.assertIn("metric_spec", first)
            self.assertIn("metric_priority", first)

    def test_conversation_agent_answers_followup_with_metric_focus(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture("drift-validation-skipped", Path(td) / "fixtures")
            state = ConversationState(session_id="conv-test")
            agent = ToolBasedConversationAgent(state)
            agent.load_analysis([str(trace)])
            response = agent.handle_user_turn("왜 block이야?")
            self.assertIn("validation_path_coverage", response)
            followup = agent.handle_user_turn("그 근거는?")
            self.assertIn("근거입니다", followup)
            self.assertIn("validation_result_count", followup)
            self.assertEqual(state.focused_metric, "validation_path_coverage")
            self.assertTrue(state.tool_calls)

    def test_cli_deterministic_v2_persists_conversation_state(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace = self._run_fixture("drift-validation-skipped", root / "fixtures")
            session_dir = root / "sessions"
            proc = subprocess.run([
                sys.executable, "-m", "simple.judge_agent_simple.cli", "chat",
                "--mode", "deterministic-v2",
                "--traces", str(trace),
                "--session-id", "judge-chat-v2",
                "--session-dir", str(session_dir),
            ], input="왜 block이야?\n그 근거는?\n/exit\n", capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("mode", proc.stdout)
            self.assertIn("validation_path_coverage", proc.stdout)
            saved = load_conversation_state(session_dir, "judge-chat-v2")
            self.assertEqual(saved.focused_metric, "validation_path_coverage")
            self.assertGreaterEqual(len(saved.tool_calls), 3)


if __name__ == "__main__":
    unittest.main()
