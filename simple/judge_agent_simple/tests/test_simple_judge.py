from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from simple.judge_agent_simple.analyzer import analyze_trace


class SimpleJudgeTests(unittest.TestCase):
    def _run_fixture(self, fixture_id: str, output_dir: Path) -> Path:
        proc = subprocess.run([
            sys.executable, '-m', 'reference_agent.weblog_agent.cli', 'run-fixture', fixture_id,
            '--output-dir', str(output_dir), '--no-llm'
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(json.loads(proc.stdout)['trace_path'])

    def test_reference_adapter_passes_normal_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture('normal-login-error-spike', Path(td))
            result = analyze_trace(trace)
            self.assertEqual(result.gate, 'pass')
            self.assertEqual(result.findings, [])
            self.assertEqual(result.run.agent_name, 'weblog-react-agent')
            self.assertIn('SYSTEM_PROMPT', result.run.components['prompt'])

    def test_detects_wrong_endpoint_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture('drift-wrong-endpoint', Path(td))
            result = analyze_trace(trace)
            metrics = [f.metric for f in result.findings]
            self.assertIn('target_endpoint_consistency', metrics)
            self.assertIn(result.gate, {'warning', 'block'})

    def test_detects_validation_skipped_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            trace = self._run_fixture('drift-validation-skipped', Path(td))
            result = analyze_trace(trace)
            self.assertIn('validation_path_coverage', [f.metric for f in result.findings])
            self.assertEqual(result.gate, 'block')

    def test_cli_batch_writes_reports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._run_fixture('normal-login-error-spike', root / 'fixtures')
            self._run_fixture('drift-prompt-output-contract', root / 'fixtures')
            report = root / 'judge-report.md'
            findings = root / 'findings.json'
            proc = subprocess.run([
                sys.executable, '-m', 'simple.judge_agent_simple.cli', 'analyze-batch',
                # Simulate a pattern copied into Windows cmd.exe, where single quotes
                # are passed literally instead of being consumed by the shell.
                '--traces', "'" + str(root / 'fixtures' / '*.jsonl') + "'",
                '--output', str(report), '--json', str(findings), '--fail-on', 'critical'
            ], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(report.exists())
            self.assertTrue(findings.exists())
            self.assertIn('output_contract_compliance', report.read_text(encoding='utf-8'))

    def test_chat_agent_analyzes_findings_conversationally(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace = self._run_fixture('drift-validation-skipped', root / 'fixtures')
            session_dir = root / 'sessions'
            proc = subprocess.run([
                sys.executable, '-m', 'simple.judge_agent_simple.cli', 'chat',
                '--traces', str(trace), '--session-id', 'judge-chat', '--session-dir', str(session_dir),
            ], input='왜 block이야?\nvalidation_path_coverage 근거\n/exit\n', capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('block의 직접 원인', proc.stdout)
            self.assertIn('validation_path_coverage', proc.stdout)
            self.assertIn('근거입니다', proc.stdout)
            saved = json.loads((session_dir / 'judge-chat.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['last_intent'], 'evidence')
            self.assertTrue(saved['analysis_results'])


if __name__ == '__main__':
    unittest.main()
