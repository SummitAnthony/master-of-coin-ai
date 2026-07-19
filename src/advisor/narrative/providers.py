"""Concrete LLM backends.

Gemini is implemented over the Generative Language REST API using httpx (no
vendor SDK, so it stays offline-mockable and PyInstaller-friendly). The other
providers are selectable stubs whose ``generate`` raises NotImplementedError.
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx

from .client import LLMClient
from .errors import LLMResponseError, MissingAPIKeyError


class GeminiClient(LLMClient):
    """Default backend (Gemini free tier) over the v1beta REST API."""

    provider = "gemini"
    BASE_URL: ClassVar[str] = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-1.5-flash",
        temperature: float = 0.0,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise MissingAPIKeyError("gemini")
        self._api_key = api_key
        self.model = model
        self.temperature = temperature
        self._client = http_client if http_client is not None else httpx.Client(timeout=timeout)
        self._owns_client = http_client is None

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        url = f"{self.BASE_URL}/models/{self.model}:generateContent"
        try:
            response = self._client.post(
                url, params={"key": self._api_key}, json=self._build_payload(prompt, system)
            )
            response.raise_for_status()
            data: Any = response.json()
        except httpx.HTTPError as exc:
            # Emit only the exception type so a URL carrying the key never leaks.
            raise LLMResponseError("gemini", f"transport error: {type(exc).__name__}") from exc
        return self._parse_response(data)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _build_payload(self, prompt: str, system: str | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": self.temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    @staticmethod
    def _parse_response(data: Any) -> str:
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError("gemini", "unexpected response shape") from exc
        if not isinstance(text, str) or not text.strip():
            raise LLMResponseError("gemini", "empty completion")
        return text

    def __repr__(self) -> str:
        return f"GeminiClient(model={self.model!r})"  # never renders the api key


class OpenAIClient(LLMClient):
    """Selectable stub for OpenAI."""

    provider = "openai"

    def __init__(self, api_key: str, *, model: str = "gpt-4o-mini", **_kwargs: Any) -> None:
        if not api_key or not api_key.strip():
            raise MissingAPIKeyError("openai")
        self.model = model

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError("OpenAI provider is not implemented yet")


class AnthropicClient(LLMClient):
    """Selectable stub for Anthropic."""

    provider = "anthropic"

    def __init__(
        self, api_key: str, *, model: str = "claude-3-5-sonnet-latest", **_kwargs: Any
    ) -> None:
        if not api_key or not api_key.strip():
            raise MissingAPIKeyError("anthropic")
        self.model = model

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError("Anthropic provider is not implemented yet")


class OllamaClient(LLMClient):
    """Selectable stub for a local Ollama server (its base_url is its credential)."""

    provider = "ollama"

    def __init__(self, base_url: str, *, model: str = "llama3.1", **_kwargs: Any) -> None:
        if not base_url or not base_url.strip():
            raise MissingAPIKeyError("ollama")
        self.model = model

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError("Ollama provider is not implemented yet")
