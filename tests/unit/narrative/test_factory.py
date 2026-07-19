"""Tests for provider selection in get_llm_client."""

from __future__ import annotations

import pytest

from advisor.config import LLMProvider
from advisor.narrative.errors import MissingAPIKeyError
from advisor.narrative.factory import DEFAULT_MODELS, get_llm_client
from advisor.narrative.providers import AnthropicClient, GeminiClient, OllamaClient, OpenAIClient

from .conftest import settings_for


def test_selects_gemini_by_default() -> None:
    client = get_llm_client(settings_for(LLMProvider.gemini, with_key=True))
    assert isinstance(client, GeminiClient)
    assert client.provider == "gemini"
    assert client.model == DEFAULT_MODELS["gemini"]


@pytest.mark.parametrize(
    "provider,cls",
    [
        (LLMProvider.openai, OpenAIClient),
        (LLMProvider.anthropic, AnthropicClient),
        (LLMProvider.ollama, OllamaClient),
    ],
)
def test_selects_each_provider(provider: LLMProvider, cls: type) -> None:
    client = get_llm_client(settings_for(provider, with_key=True))
    assert isinstance(client, cls)


@pytest.mark.parametrize(
    "provider",
    [LLMProvider.gemini, LLMProvider.openai, LLMProvider.anthropic, LLMProvider.ollama],
)
def test_missing_credential_raises(provider: LLMProvider) -> None:
    with pytest.raises(MissingAPIKeyError) as ei:
        get_llm_client(settings_for(provider, with_key=False))
    assert ei.value.provider == provider.value


def test_model_override_from_settings() -> None:
    settings = settings_for(LLMProvider.gemini, with_key=True).model_copy(
        update={"llm_model": "gemini-pro"}
    )
    assert get_llm_client(settings).model == "gemini-pro"
