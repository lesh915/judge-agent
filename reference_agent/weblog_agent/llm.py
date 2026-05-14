from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


DEFAULT_ENV_PATHS = (
    Path("reference_agent/weblog_agent/.env"),
    Path(".env"),
)


def load_env_file(path: Union[str, Path], *, override: bool = False) -> Dict[str, str]:
    """Load KEY=VALUE pairs from an env file without requiring python-dotenv."""

    env_path = Path(path)
    loaded: Dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        loaded[key] = value
        if override or key not in os.environ:
            os.environ[key] = value
    return loaded


def load_llm_env() -> Optional[Path]:
    """Load LLM env from WEBLOG_AGENT_ENV_FILE or conventional local files."""

    explicit = os.getenv("WEBLOG_AGENT_ENV_FILE")
    if explicit:
        load_env_file(explicit, override=False)
        return Path(explicit)
    for path in DEFAULT_ENV_PATHS:
        if path.exists():
            load_env_file(path, override=False)
            return path
    return None


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class LLMConfig:
    """OpenAI-compatible LLM endpoint configuration.

    This supports OpenAI, local OpenAI-compatible servers such as vLLM/Ollama
    OpenAI mode/LM Studio, and arbitrary reachable OpenAI-compatible URLs.
    """

    provider: str = "openai-compatible"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    chat_completions_path: str = "/chat/completions"
    api_key_env: str = "OPENAI_API_KEY"
    api_key: Optional[str] = None
    require_api_key: bool = True
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    temperature: float = 0.2
    timeout_seconds: int = 45
    extra_headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        load_llm_env()
        extra_headers: Dict[str, str] = {}
        raw_headers = os.getenv("WEBLOG_AGENT_LLM_EXTRA_HEADERS_JSON", "").strip()
        if raw_headers:
            extra_headers = json.loads(raw_headers)

        api_key_env = os.getenv("WEBLOG_AGENT_LLM_API_KEY_ENV", os.getenv("WEBLOG_AGENT_API_KEY_ENV", "OPENAI_API_KEY"))
        api_key = os.getenv("WEBLOG_AGENT_LLM_API_KEY") or os.getenv(api_key_env)

        base_url = os.getenv("WEBLOG_AGENT_LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
        require_api_key_default = not ("localhost" in base_url or "127.0.0.1" in base_url or "0.0.0.0" in base_url)

        return cls(
            provider=os.getenv("WEBLOG_AGENT_LLM_PROVIDER", os.getenv("WEBLOG_AGENT_LLM_TYPE", "openai-compatible")),
            model=os.getenv("WEBLOG_AGENT_LLM_MODEL", os.getenv("WEBLOG_AGENT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))),
            base_url=base_url,
            chat_completions_path=os.getenv("WEBLOG_AGENT_LLM_CHAT_COMPLETIONS_PATH", "/chat/completions"),
            api_key_env=api_key_env,
            api_key=api_key,
            require_api_key=_bool_env("WEBLOG_AGENT_LLM_REQUIRE_API_KEY", require_api_key_default),
            auth_header=os.getenv("WEBLOG_AGENT_LLM_AUTH_HEADER", "Authorization"),
            auth_scheme=os.getenv("WEBLOG_AGENT_LLM_AUTH_SCHEME", "Bearer"),
            temperature=float(os.getenv("WEBLOG_AGENT_LLM_TEMPERATURE", os.getenv("WEBLOG_AGENT_TEMPERATURE", "0.2"))),
            timeout_seconds=int(os.getenv("WEBLOG_AGENT_LLM_TIMEOUT_SECONDS", os.getenv("WEBLOG_AGENT_TIMEOUT_SECONDS", "45"))),
            extra_headers=extra_headers,
        )

    @property
    def endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/" + self.chat_completions_path.lstrip("/")

    def sanitized(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "chat_completions_path": self.chat_completions_path,
            "api_key_env": self.api_key_env,
            "require_api_key": self.require_api_key,
            "auth_header": self.auth_header,
            "auth_scheme": self.auth_scheme,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "extra_headers": sorted(self.extra_headers.keys()),
        }


class LLMClient:
    """Small OpenAI-compatible chat client used by the reference agent."""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()

    @property
    def enabled(self) -> bool:
        return bool(self.config.model and self.config.base_url and (self.config.api_key or not self.config.require_api_key))

    def chat(self, messages: List[Dict[str, str]], *, response_format: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if self.config.require_api_key and not self.config.api_key:
            raise RuntimeError(f"LLM API key not configured: set WEBLOG_AGENT_LLM_API_KEY or {self.config.api_key_env}")

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {"Content-Type": "application/json", **self.config.extra_headers}
        if self.config.api_key:
            auth_value = self.config.api_key if not self.config.auth_scheme else f"{self.config.auth_scheme} {self.config.api_key}"
            headers[self.config.auth_header] = auth_value

        req = urllib.request.Request(
            self.config.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
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
