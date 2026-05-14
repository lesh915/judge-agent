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

    def test_chat_session_persists_context_and_answers_followup(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            session_dir = root / 'sessions'
            trace_dir = root / 'traces'
            report_dir = root / 'reports'
            user_script = '지난 1시간 동안 /api/login 5xx 에러율을 분석해주세요\n방금 결과에서 가장 의심되는 원인은?\n/exit\n'
            proc = subprocess.run([
                sys.executable, '-m', 'reference_agent.weblog_agent.cli', 'chat',
                '--session-id', 'test-chat',
                '--session-dir', str(session_dir),
                '--trace-dir', str(trace_dir),
                '--report-dir', str(report_dir),
                '--no-llm',
            ], input=user_script, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            first_line = proc.stdout.splitlines()[0]
            data = json.loads(first_line)
            self.assertEqual(data['session_id'], 'test-chat')
            session_path = session_dir / 'test-chat.json'
            self.assertTrue(session_path.exists())
            saved = json.loads(session_path.read_text())
            self.assertEqual(len(saved['turns']), 4)
            self.assertIsNotNone(saved['last_analysis'])
            self.assertIn('error_rate', saved['last_analysis']['metrics'])
            self.assertTrue((trace_dir / 'test-chat-chat.jsonl').exists())
            self.assertTrue((trace_dir / 'test-chat-turn-1.jsonl').exists())
            self.assertTrue((report_dir / 'test-chat-turn-1.md').exists())
            trace = (trace_dir / 'test-chat-chat.jsonl').read_text()
            self.assertIn('chat_session_start', trace)
            self.assertIn('chat_intent_classified', trace)
            self.assertIn('chat_context_built', trace)
            self.assertIn('chat_analysis_invoked', trace)
            self.assertIn('chat_response_generated', trace)
            self.assertIn('가능성이 가장 큰 원인', proc.stdout)

    def test_list_sessions_outputs_json(self):
        with tempfile.TemporaryDirectory() as td:
            session_dir = Path(td) / 'sessions'
            subprocess.run([
                sys.executable, '-m', 'reference_agent.weblog_agent.cli', 'chat',
                '--session-id', 'listed-chat', '--session-dir', str(session_dir), '--no-llm'
            ], input='/exit\n', capture_output=True, text=True, check=True)
            proc = subprocess.run([sys.executable, '-m', 'reference_agent.weblog_agent.cli', 'list-sessions', '--session-dir', str(session_dir)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data[0]['session_id'], 'listed-chat')

if __name__ == '__main__':
    unittest.main()
