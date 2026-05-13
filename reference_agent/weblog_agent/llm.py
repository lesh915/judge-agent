from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.2
    timeout_seconds: int = 45

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.getenv("WEBLOG_AGENT_LLM_PROVIDER", "openai"),
            model=os.getenv("WEBLOG_AGENT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key_env=os.getenv("WEBLOG_AGENT_API_KEY_ENV", "OPENAI_API_KEY"),
            temperature=float(os.getenv("WEBLOG_AGENT_TEMPERATURE", "0.2")),
            timeout_seconds=int(os.getenv("WEBLOG_AGENT_TIMEOUT_SECONDS", "45")),
        )


class LLMClient:
    """Small OpenAI-compatible chat client used by the reference agent.

    The implementation intentionally uses the Python standard library so the
    reference agent can run in a clean test environment. If OPENAI_API_KEY (or
    WEBLOG_AGENT_API_KEY_ENV) is not set, the caller can fall back to a
    deterministic implementation while still emitting an llm_skipped trace event.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()

    @property
    def enabled(self) -> bool:
        return bool(os.getenv(self.config.api_key_env))

    def chat(self, messages: List[Dict[str, str]], *, response_format: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        api_key = os.getenv(self.config.api_key_env)
        if not api_key:
            raise RuntimeError(f"LLM API key not configured: {self.config.api_key_env}")

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        req = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP error {exc.code}: {body[:500]}") from exc
        data = json.loads(raw)
        content = data["choices"][0]["message"].get("content", "")
        return {
            "id": data.get("id"),
            "model": data.get("model", self.config.model),
            "content": content,
            "usage": data.get("usage", {}),
            "latency_ms": int((time.time() - started) * 1000),
        }


def parse_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
