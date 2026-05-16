from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reference_agent.weblog_agent.llm import LLMConfig, LLMClient, load_env_file


class LLMConfigTests(unittest.TestCase):
    def test_load_env_file_and_local_openai_compatible_endpoint_without_key(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "agent.env"
            env_path.write_text("\n".join([
                "WEBLOG_AGENT_LLM_BASE_URL=http://localhost:1234/v1",
                "WEBLOG_AGENT_LLM_MODEL=local-qwen",
                "WEBLOG_AGENT_LLM_REQUIRE_API_KEY=false",
            ]), encoding="utf-8")
            with patch.dict(os.environ, {"WEBLOG_AGENT_ENV_FILE": str(env_path)}, clear=True):
                config = LLMConfig.from_env()
                client = LLMClient(config)

        self.assertEqual(config.base_url, "http://localhost:1234/v1")
        self.assertEqual(config.model, "local-qwen")
        self.assertFalse(config.require_api_key)
        self.assertTrue(client.enabled)
        self.assertEqual(config.endpoint, "http://localhost:1234/v1/chat/completions")

    def test_openai_compatible_gateway_can_use_custom_api_key_env(self):
        env = {
            "WEBLOG_AGENT_LLM_BASE_URL": "https://llm-gateway.example.com/v1",
            "WEBLOG_AGENT_LLM_MODEL": "company-model",
            "WEBLOG_AGENT_LLM_REQUIRE_API_KEY": "true",
            "WEBLOG_AGENT_LLM_API_KEY_ENV": "COMPANY_LLM_KEY",
            "COMPANY_LLM_KEY": "secret-value",
        }
        with patch.dict(os.environ, env, clear=True):
            config = LLMConfig.from_env()
            client = LLMClient(config)

        self.assertEqual(config.api_key_env, "COMPANY_LLM_KEY")
        self.assertEqual(config.api_key, "secret-value")
        self.assertTrue(client.enabled)
        self.assertNotIn("api_key", config.sanitized())

    def test_load_env_file_does_not_override_existing_env_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / "agent.env"
            env_path.write_text("WEBLOG_AGENT_LLM_MODEL=file-model\n", encoding="utf-8")
            with patch.dict(os.environ, {"WEBLOG_AGENT_LLM_MODEL": "shell-model"}, clear=True):
                load_env_file(env_path)
                self.assertEqual(os.environ["WEBLOG_AGENT_LLM_MODEL"], "shell-model")


if __name__ == "__main__":
    unittest.main()
