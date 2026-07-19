"""Map settings (LLM_PROVIDER + credentials) to a constructed LLM client."""

from __future__ import annotations

from typing import Final

import httpx

from advisor.config import LLMProvider, Settings

from .client import LLMClient
from .errors import MissingAPIKeyError
from .providers import AnthropicClient, GeminiClient, OllamaClient, OpenAIClient

SUPPORTED_PROVIDERS: Final[tuple[str, ...]] = ("gemini", "openai", "anthropic", "ollama")
DEFAULT_MODELS: Final[dict[str, str]] = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "ollama": "llama3.1",
}


def get_llm_client(settings: Settings, *, http_client: httpx.Client | None = None) -> LLMClient:
    """Construct the client for the configured provider, enforcing credentials."""
    provider = settings.llm_provider
    model = settings.llm_model or DEFAULT_MODELS[provider.value]

    if provider is LLMProvider.ollama:
        if not settings.ollama_base_url.strip():
            raise MissingAPIKeyError("ollama")
        return OllamaClient(settings.ollama_base_url, model=model)

    key = settings.api_key_for_provider()
    if key is None or not key.get_secret_value().strip():
        raise MissingAPIKeyError(provider.value)
    secret = key.get_secret_value()

    if provider is LLMProvider.gemini:
        return GeminiClient(
            secret,
            model=model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout,
            http_client=http_client,
        )
    if provider is LLMProvider.openai:
        return OpenAIClient(secret, model=model)
    return AnthropicClient(secret, model=model)
