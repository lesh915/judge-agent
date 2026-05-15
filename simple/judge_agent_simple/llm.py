from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


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


class OpenAIChatClient:
    """Tiny stdlib OpenAI chat-completions client.

    This avoids adding a required runtime dependency. It is only used when
    OPENAI_API_KEY is present or explicitly requested by code.
    """

    provider = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1/chat/completions"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def complete(self, messages: List[Dict[str, str]], *, temperature: float = 0.0) -> LlmResult:
        payload = json.dumps({"model": self.model, "messages": messages, "temperature": temperature}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return LlmResult(content="", model=self.model, provider=self.provider, used_fallback=True, raw={"error": str(exc)})
        content = raw.get("choices", [{}])[0].get("message", {}).get("content") or ""
        return LlmResult(content=content, model=self.model, provider=self.provider, raw=raw)


def create_llm_client(provider: str = "auto", model: Optional[str] = None) -> LlmClient:
    provider = provider.lower()
    if provider in {"none", "off", "deterministic"}:
        return UnavailableLlmClient("LLM disabled")
    if provider == "mock":
        return MockLlmClient()
    if provider in {"auto", "openai"}:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            return OpenAIChatClient(api_key=api_key, model=model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
        if provider == "openai":
            return UnavailableLlmClient("OPENAI_API_KEY is not set")
    return UnavailableLlmClient("No supported LLM provider is configured")
