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
            trace = Path(data['trace_path']).read_text()
            self.assertIn('node_start', trace)
            self.assertIn('tool_start', trace)

if __name__ == '__main__':
    unittest.main()
