import json
import tempfile
import unittest
from pathlib import Path

from simple.judge_agent_simple.core.config import default_config_dir, load_config
from simple.judge_agent_simple.core.metrics import get_metric, list_metrics


class ConfigFilesTest(unittest.TestCase):
    def test_bundled_config_files_exist(self):
        base = default_config_dir()
        for name in ["app.json", "metrics.json", "detector_rules.json", "conversation.json", "llm_profiles.json", "database_tables.md"]:
            self.assertTrue((base / name).exists(), name)

    def test_metric_registry_is_loaded_from_config(self):
        metric = get_metric("validation_path_coverage")
        self.assertIsNotNone(metric)
        self.assertEqual(metric.severity, "Critical")
        self.assertGreaterEqual(len(list_metrics()), 30)

    def test_load_config_supports_directory_override(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "app.json"
            path.write_text(json.dumps({"defaults": {"adapter": "custom"}}), encoding="utf-8")
            data = load_config("app.json", config_dir_override=td)
            self.assertEqual(data["defaults"]["adapter"], "custom")


if __name__ == "__main__":
    unittest.main()
