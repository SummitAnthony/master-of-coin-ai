"""Narrative layer.

Provider-agnostic LLM adapter. Receives only the frozen ``Facts`` object and
writes prose about it; it never sees raw inputs and never computes figures.
"""

from __future__ import annotations

from .advisor import Advisory, advisor
from .client import LLMClient, SupportsGenerate
from .context import NarrativeContext, build_context
from .errors import (
    LLMError,
    LLMResponseError,
    MissingAPIKeyError,
    ProviderNotImplementedError,
)
from .factory import SUPPORTED_PROVIDERS, get_llm_client
from .templates import PromptTemplates, load_templates

__all__ = [
    "SUPPORTED_PROVIDERS",
    "Advisory",
    "LLMClient",
    "LLMError",
    "LLMResponseError",
    "MissingAPIKeyError",
    "NarrativeContext",
    "PromptTemplates",
    "ProviderNotImplementedError",
    "SupportsGenerate",
    "advisor",
    "build_context",
    "get_llm_client",
    "load_templates",
]
