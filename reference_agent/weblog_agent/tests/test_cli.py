import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

class CliTests(unittest.TestCase):
    def test_run_fixture_creates_trace_and_report(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run([sys.executable, '-m', 'reference_agent.weblog_agent.cli', 'run-fixture', 'normal-login-error-spike', '--output-dir', td, '--no-llm'], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertTrue(Path(data['trace_path']).exists())
            self.assertTrue(Path(data['report_path']).exists())
            report = Path(data['report_path']).read_text()
            self.assertIn('## Evidence', report)
            self.assertIn('## RAG Context', report)
            self.assertIn('## MCP Context', report)
            trace = Path(data['trace_path']).read_text()
            self.assertIn('node_start', trace)
            self.assertIn('tool_start', trace)
            self.assertIn('react_step', trace)
            self.assertIn('mcp_start', trace)
            self.assertIn('tools/list', trace)
            self.assertIn('tools/call', trace)
            self.assertIn('agent_components', trace)

if __name__ == '__main__':
    unittest.main()
