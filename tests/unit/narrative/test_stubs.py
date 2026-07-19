"""Tests for the selectable stub providers."""

from __future__ import annotations

import pytest

from advisor.narrative.errors import MissingAPIKeyError
from advisor.narrative.providers import AnthropicClient, OllamaClient, OpenAIClient


def test_stubs_construct_with_credential() -> None:
    assert OpenAIClient("k").provider == "openai"
    assert AnthropicClient("k").provider == "anthropic"
    assert OllamaClient("http://x").provider == "ollama"


@pytest.mark.parametrize(
    "factory",
    [lambda: OpenAIClient(""), lambda: AnthropicClient(""), lambda: OllamaClient("")],
)
def test_blank_credential_raises(factory: object) -> None:
    with pytest.raises(MissingAPIKeyError):
        factory()  # type: ignore[operator]


def test_generate_raises_not_implemented() -> None:
    for client in (OpenAIClient("k"), AnthropicClient("k"), OllamaClient("http://x")):
        with pytest.raises(NotImplementedError):
            client.generate("hi")
