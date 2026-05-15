from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from simple.judge_agent_simple.conversation_state import ConversationState
from simple.judge_agent_simple.graph import GraphConversationAgent, langgraph_available
from simple.judge_agent_simple.llm import UnavailableLlmClient


class GraphAgentTests(unittest.TestCase):
    def _run_fixture(self, fixture_id: str, output_dir: Path) -> Path:
        proc = subprocess.run([
            sys.executable, "-m", "reference_agent.weblog_agent.cli", "run-fixture", fixture_id,
            "--output-dir", str(output_dir), "--no-llm",
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(json.loads(proc.stdout)["trace_path"])

    def test_graph_agent_runs_or_falls_back(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture("drift-validation-skipped", Path(td) / "fixtures")
            state = ConversationState(session_id="graph-test")
            agent = GraphConversationAgent(state, llm=UnavailableLlmClient("test"))
            agent.load_analysis([str(trace)])
            response = agent.handle_user_turn("왜 block이야?")
            self.assertIn("validation_path_coverage", response)
            self.assertIn(agent.graph_runtime, {"langgraph", "fallback"})
            self.assertEqual(state.focused_metric, "validation_path_coverage")

    def test_require_langgraph_raises_when_missing(self):
        if langgraph_available():
            self.skipTest("LangGraph is installed")
        with self.assertRaises(RuntimeError):
            GraphConversationAgent(ConversationState(session_id="missing"), require_langgraph=True)

    def test_cli_graph_mode_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace = self._run_fixture("drift-validation-skipped", root / "fixtures")
            proc = subprocess.run([
                sys.executable, "-m", "simple.judge_agent_simple.cli", "chat",
                "--mode", "graph",
                "--llm-provider", "none",
                "--traces", str(trace),
                "--session-id", "graph-cli",
                "--session-dir", str(root / "sessions"),
            ], input="왜 block이야?\n/exit\n", capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("validation_path_coverage", proc.stdout)
            self.assertIn("mode", proc.stdout)


if __name__ == "__main__":
    unittest.main()
