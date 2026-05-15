from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from simple.judge_agent_simple.conversation_agent import HybridConversationAgent
from simple.judge_agent_simple.conversation_state import ConversationState
from simple.judge_agent_simple.llm import MockLlmClient, UnavailableLlmClient


class HybridAgentTests(unittest.TestCase):
    def _run_fixture(self, fixture_id: str, output_dir: Path) -> Path:
        proc = subprocess.run([
            sys.executable, "-m", "reference_agent.weblog_agent.cli", "run-fixture", fixture_id,
            "--output-dir", str(output_dir), "--no-llm",
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(json.loads(proc.stdout)["trace_path"])

    def test_hybrid_uses_mock_llm_after_tool_execution(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture("drift-validation-skipped", Path(td) / "fixtures")
            state = ConversationState(session_id="hybrid-test")
            llm = MockLlmClient("LLM synthesized grounded answer")
            agent = HybridConversationAgent(state, llm=llm)
            agent.load_analysis([str(trace)])
            response = agent.handle_user_turn("왜 block이야?")
            self.assertEqual(response, "LLM synthesized grounded answer")
            self.assertTrue(llm.calls)
            prompt_payload = llm.calls[-1][-1]["content"]
            self.assertIn("validation_path_coverage", prompt_payload)
            self.assertEqual(state.focused_metric, "validation_path_coverage")

    def test_hybrid_falls_back_when_llm_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture("drift-validation-skipped", Path(td) / "fixtures")
            state = ConversationState(session_id="hybrid-fallback")
            agent = HybridConversationAgent(state, llm=UnavailableLlmClient("test"))
            agent.load_analysis([str(trace)])
            response = agent.handle_user_turn("왜 block이야?")
            self.assertIn("validation_path_coverage", response)
            self.assertIn("hybrid fallback", response)

    def test_cli_hybrid_mock_mode(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace = self._run_fixture("drift-validation-skipped", root / "fixtures")
            proc = subprocess.run([
                sys.executable, "-m", "simple.judge_agent_simple.cli", "chat",
                "--mode", "hybrid",
                "--llm-provider", "mock",
                "--traces", str(trace),
                "--session-id", "hybrid-cli",
                "--session-dir", str(root / "sessions"),
            ], input="왜 block이야?\n/exit\n", capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("[mock synthesized]", proc.stdout)
            self.assertIn("validation_path_coverage", proc.stdout)


if __name__ == "__main__":
    unittest.main()
