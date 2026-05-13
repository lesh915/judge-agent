import unittest
from reference_agent.weblog_agent import tools
from reference_agent.weblog_agent.fixtures import FIXTURE_DIR

class ToolTests(unittest.TestCase):
    def test_read_parse_filter_metrics(self):
        raw = tools.read_log_file(str(FIXTURE_DIR / 'access.log'))
        parsed = tools.parse_access_log(raw['lines'])
        self.assertEqual(parsed['parse_error_count'], 0)
        filtered = tools.filter_log_records(parsed['records'], path_pattern='/api/login', status_min=0, status_max=599)
        self.assertEqual(filtered['matched_count'], 80)
        metrics = tools.compute_log_metrics(filtered['records'])
        self.assertEqual(metrics['request_count'], 80)
        self.assertEqual(metrics['5xx_count'], 12)
        self.assertEqual(metrics['error_rate'], 0.15)

if __name__ == '__main__':
    unittest.main()
