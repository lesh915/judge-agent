from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from simple.judge_agent_simple.llm.clients import OpenAICompatibleChatClient, UnavailableLlmClient, create_llm_client, load_llm_config, parse_env_file


class LlmConfigTests(unittest.TestCase):
    def test_parse_env_file(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("""
# comment
JUDGE_LLM_PROVIDER=openai-compatible
JUDGE_LLM_MODEL='local-model'
JUDGE_LLM_BASE_URL=\"http://localhost:8000/v1\"
JUDGE_LLM_API_KEY=local
""", encoding="utf-8")
            values = parse_env_file(env)
            self.assertEqual(values["JUDGE_LLM_PROVIDER"], "openai-compatible")
            self.assertEqual(values["JUDGE_LLM_MODEL"], "local-model")
            self.assertEqual(values["JUDGE_LLM_BASE_URL"], "http://localhost:8000/v1")

    def test_load_llm_config_from_env_file(self):
        with tempfile.TemporaryDirectory() as td:
            env = Path(td) / ".env"
            env.write_text("""
JUDGE_LLM_PROVIDER=lmstudio
JUDGE_LLM_MODEL=qwen-local
JUDGE_LLM_BASE_URL=http://localhost:1234/v1
JUDGE_LLM_API_KEY=local
JUDGE_LLM_TIMEOUT_SECONDS=5
""", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                config = load_llm_config(env_file=str(env))
            self.assertEqual(config.provider, "lmstudio")
            self.assertEqual(config.model, "qwen-local")
            self.assertEqual(config.base_url, "http://localhost:1234/v1")
            self.assertEqual(config.chat_completions_url, "http://localhost:1234/v1/chat/completions")
            self.assertEqual(config.timeout_seconds, 5)

    def test_create_openai_compatible_client_for_local_provider(self):
        with patch.dict(os.environ, {}, clear=True):
            client = create_llm_client(provider="ollama", model="llama3.1")
        self.assertIsInstance(client, OpenAICompatibleChatClient)
        self.assertEqual(client.model, "llama3.1")
        self.assertEqual(client.base_url, "http://localhost:11434/v1/chat/completions")

    def test_openai_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            client = create_llm_client(provider="openai")
        self.assertIsInstance(client, UnavailableLlmClient)

    def test_auto_without_config_falls_back(self):
        with patch.dict(os.environ, {}, clear=True):
            client = create_llm_client(provider="auto")
        self.assertIsInstance(client, UnavailableLlmClient)


if __name__ == "__main__":
    unittest.main()
