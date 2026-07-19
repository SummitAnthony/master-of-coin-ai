"""Tests for GeminiClient using an offline httpx MockTransport (no real network)."""

from __future__ import annotations

import httpx
import pytest

from advisor.narrative.errors import LLMResponseError, MissingAPIKeyError
from advisor.narrative.providers import GeminiClient

_OK_PAYLOAD = {"candidates": [{"content": {"parts": [{"text": "hello world"}]}}]}


def _client(handler: object) -> GeminiClient:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    return GeminiClient("secret-key", http_client=httpx.Client(transport=transport))


def test_blank_key_raises() -> None:
    with pytest.raises(MissingAPIKeyError):
        GeminiClient("")


def test_generate_happy_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "generateContent" in str(request.url)
        assert request.url.params.get("key") == "secret-key"
        return httpx.Response(200, json=_OK_PAYLOAD)

    assert _client(handler).generate("hi", system="sys") == "hello world"


def test_build_payload_temperature_and_system() -> None:
    client = GeminiClient("k", temperature=0.0)
    payload = client._build_payload("hi", "sys")
    assert payload["generationConfig"]["temperature"] == 0.0
    assert payload["systemInstruction"]["parts"][0]["text"] == "sys"


def test_http_error_wrapped_and_scrubbed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(LLMResponseError) as ei:
        _client(handler).generate("hi")
    assert "secret-key" not in str(ei.value)


def test_empty_candidates_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    with pytest.raises(LLMResponseError):
        _client(handler).generate("hi")


def test_repr_does_not_leak_key() -> None:
    assert "secret-key" not in repr(GeminiClient("secret-key"))
