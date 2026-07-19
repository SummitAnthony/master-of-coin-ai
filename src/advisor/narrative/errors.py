"""Typed, secret-free errors for the narrative/LLM layer."""

from __future__ import annotations


class LLMError(Exception):
    """Base class for all narrative/LLM failures."""


class MissingAPIKeyError(LLMError):
    """No API key / credential configured for the selected provider."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"No API key/credential configured for provider {provider!r}")


class ProviderNotImplementedError(LLMError):
    """A selectable but not-yet-implemented provider was invoked."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"Provider {provider!r} is selectable but not implemented")


class LLMResponseError(LLMError):
    """Transport/HTTP/empty-response failure. ``detail`` is scrubbed of secrets."""

    def __init__(self, provider: str, detail: str) -> None:
        self.provider = provider
        self.detail = detail
        super().__init__(f"LLM provider {provider!r} failed: {detail}")
