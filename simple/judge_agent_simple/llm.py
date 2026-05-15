from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class LlmConfig:
    provider: str = "auto"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout_seconds: float = 30.0
    temperature: float = 0.0
    env_file: Optional[str] = None

    @property
    def chat_completions_url(self) -> str:
        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"


@dataclass
class LlmResult:
    content: str
    model: str = "none"
    provider: str = "none"
    used_fallback: bool = False
    raw: Optional[Dict[str, Any]] = None


class LlmClient(Protocol):
    provider: str
    model: str

    def complete(self, messages: List[Dict[str, str]], *, temperature: float = 0.0) -> LlmResult:
        ...


class UnavailableLlmClient:
    provider = "none"
    model = "deterministic-fallback"

    def __init__(self, reason: str = "LLM provider is not configured"):
        self.reason = reason

    def complete(self, messages: List[Dict[str, str]], *, temperature: float = 0.0) -> LlmResult:
        return LlmResult(content="", model=self.model, provider=self.provider, used_fallback=True, raw={"reason": self.reason})


class MockLlmClient:
    """Test double that returns a deterministic prefix plus the latest user content."""

    provider = "mock"
    model = "mock-llm"

    def __init__(self, content: Optional[str] = None):
        self.content = content
        self.calls: List[List[Dict[str, str]]] = []

    def complete(self, messages: List[Dict[str, str]], *, temperature: float = 0.0) -> LlmResult:
        self.calls.append(messages)
        if self.content is not None:
            return LlmResult(content=self.content, model=self.model, provider=self.provider)
        last = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        return LlmResult(content=f"[mock synthesized]\n{last}", model=self.model, provider=self.provider)


class OpenAICompatibleChatClient:
    """Stdlib Chat Completions client for OpenAI-compatible endpoints.

    Works with OpenAI, vLLM, LM Studio, Ollama OpenAI-compatible endpoints,
    llama.cpp server, LocalAI, and similar providers that implement
    POST /v1/chat/completions.
    """

    def __init__(self, config: LlmConfig):
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self.base_url = config.chat_completions_url
        self.api_key = config.api_key
        self.timeout_seconds = config.timeout_seconds

    def complete(self, messages: List[Dict[str, str]], *, temperature: float = 0.0) -> LlmResult:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        # Local OpenAI-compatible servers often ignore auth but accept any bearer token.
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.base_url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return LlmResult(content="", model=self.model, provider=self.provider, used_fallback=True, raw={"error": str(exc), "url": self.base_url})
        content = raw.get("choices", [{}])[0].get("message", {}).get("content") or ""
        return LlmResult(content=content, model=self.model, provider=self.provider, raw=raw)


# Backward-compatible name used by older code/tests.
class OpenAIChatClient(OpenAICompatibleChatClient):
    provider = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1/chat/completions"):
        super().__init__(LlmConfig(provider="openai", model=model, api_key=api_key, base_url=base_url))


def parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def load_env_file(env_file: Optional[str] = None, *, override: bool = False) -> Dict[str, str]:
    candidates: List[Path] = []
    if env_file:
        candidates.append(Path(env_file))
    else:
        cwd = Path.cwd()
        candidates.extend([cwd / ".env", cwd / "simple" / ".env"])
    loaded: Dict[str, str] = {}
    for candidate in candidates:
        values = parse_env_file(candidate)
        if not values:
            continue
        for key, value in values.items():
            if override or key not in os.environ:
                os.environ[key] = value
            loaded[key] = value
        break
    return loaded


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    return value if value not in {None, ""} else default


def _env_float(name: str, default: float) -> float:
    value = _env(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def load_llm_config(*, provider: str = "auto", model: Optional[str] = None, env_file: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None) -> LlmConfig:
    loaded = load_env_file(env_file)
    selected_provider = (provider if provider != "auto" else _env("JUDGE_LLM_PROVIDER", _env("LLM_PROVIDER", "auto"))) or "auto"
    selected_provider = selected_provider.lower()

    selected_model = model or _env("JUDGE_LLM_MODEL", _env("LLM_MODEL"))
    selected_base_url = base_url or _env("JUDGE_LLM_BASE_URL", _env("LLM_BASE_URL"))
    selected_api_key = api_key or _env("JUDGE_LLM_API_KEY", _env("LLM_API_KEY"))

    # OpenAI-compatible aliases and provider-specific fallbacks.
    if selected_provider in {"auto", "openai"}:
        selected_model = selected_model or _env("OPENAI_MODEL", "gpt-4o-mini")
        selected_api_key = selected_api_key or _env("OPENAI_API_KEY")
        selected_base_url = selected_base_url or _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    elif selected_provider in {"openai-compatible", "compatible", "local", "vllm", "lmstudio", "ollama", "localai", "llama-cpp"}:
        selected_model = selected_model or "local-model"
        # Common local defaults. Users can override with JUDGE_LLM_BASE_URL.
        if not selected_base_url:
            if selected_provider == "ollama":
                selected_base_url = "http://localhost:11434/v1"
            elif selected_provider == "lmstudio":
                selected_base_url = "http://localhost:1234/v1"
            else:
                selected_base_url = "http://localhost:8000/v1"
        selected_api_key = selected_api_key or _env("OPENAI_API_KEY") or "local"
    elif selected_provider == "mock":
        selected_model = selected_model or "mock-llm"
    else:
        selected_model = selected_model or "deterministic-fallback"

    return LlmConfig(
        provider=selected_provider,
        model=selected_model or "gpt-4o-mini",
        api_key=selected_api_key,
        base_url=selected_base_url,
        timeout_seconds=_env_float("JUDGE_LLM_TIMEOUT_SECONDS", _env_float("LLM_TIMEOUT_SECONDS", 30.0)),
        temperature=_env_float("JUDGE_LLM_TEMPERATURE", _env_float("LLM_TEMPERATURE", 0.0)),
        env_file=env_file or ("loaded" if loaded else None),
    )


def create_llm_client(provider: str = "auto", model: Optional[str] = None, *, env_file: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None) -> LlmClient:
    config = load_llm_config(provider=provider, model=model, env_file=env_file, base_url=base_url, api_key=api_key)
    provider_name = config.provider.lower()
    if provider_name in {"none", "off", "deterministic"}:
        return UnavailableLlmClient("LLM disabled")
    if provider_name == "mock":
        return MockLlmClient()
    if provider_name == "auto":
        if config.api_key or config.base_url not in {None, "https://api.openai.com/v1"}:
            return OpenAICompatibleChatClient(LlmConfig(provider="openai-compatible", model=config.model, api_key=config.api_key, base_url=config.base_url, timeout_seconds=config.timeout_seconds, temperature=config.temperature))
        return UnavailableLlmClient("No LLM provider configured. Set JUDGE_LLM_PROVIDER/JUDGE_LLM_BASE_URL or OPENAI_API_KEY.")
    if provider_name in {"openai", "openai-compatible", "compatible", "local", "vllm", "lmstudio", "ollama", "localai", "llama-cpp"}:
        if provider_name == "openai" and not config.api_key:
            return UnavailableLlmClient("OPENAI_API_KEY or JUDGE_LLM_API_KEY is not set")
        return OpenAICompatibleChatClient(config)
    return UnavailableLlmClient(f"Unsupported LLM provider: {config.provider}")
