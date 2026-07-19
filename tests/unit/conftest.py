"""Shared fixtures for unit tests.

Unit tests run in a clean temporary working directory so no stray ``.env`` is
picked up, and with configuration-related environment variables cleared, so
settings tests are deterministic regardless of the developer's environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_CONFIG_ENV = (
    "LLM_PROVIDER",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OLLAMA_BASE_URL",
    "THRESHOLDS_PATH",
    "CURRENCY",
    "VOLUME_UNIT",
    "ORG_NAME",
)


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for name in _CONFIG_ENV:
        monkeypatch.delenv(name, raising=False)
