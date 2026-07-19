"""Provider-agnostic LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


class LLMClient(ABC):
    """Base class every backend implements; advisor() depends only on this."""

    provider: str
    model: str

    @abstractmethod
    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Return the model completion text; raise LLMResponseError on failure."""

    def close(self) -> None:  # noqa: B027  (intentional concrete no-op default)
        """Release any resources (default no-op)."""


@runtime_checkable
class SupportsGenerate(Protocol):
    """Structural type accepted by advisor() so any duck-typed mock type-checks."""

    provider: str
    model: str

    def generate(self, prompt: str, *, system: str | None = None) -> str: ...
