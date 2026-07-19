"""Tests for settings loading and the fail-loud behaviour of configuration.

The ``isolated_env`` autouse fixture (see conftest) clears config env vars and
runs each test in a clean working directory.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from advisor.config import ConfigError, LLMProvider, Settings, load_settings


def test_defaults() -> None:
    s = Settings()
    assert s.llm_provider is LLMProvider.gemini
    assert s.currency == "USD"
    assert s.volume_unit == "MT"
    assert s.company_name == "Your Company"
    assert s.group_name == ""
    assert s.fiscal_year_end_month == 12
    assert s.product_name == "Master of Coin AI"
    assert s.gemini_api_key is None


def test_entity_meta_built_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANY_NAME", "A1 Polymer Ltd.")
    monkeypatch.setenv("GROUP_NAME", "Anwar Group of Industries")
    monkeypatch.setenv("CURRENCY", "BDT")
    monkeypatch.setenv("VOLUME_UNIT", "MT")
    monkeypatch.setenv("FISCAL_YEAR_END_MONTH", "6")
    entity = Settings().entity_meta()
    assert entity.company_name == "A1 Polymer Ltd."
    assert entity.group_name == "Anwar Group of Industries"
    assert entity.currency == "BDT"
    assert entity.volume_unit == "MT"
    assert entity.fiscal_year_end_month == 6


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    s = Settings()
    assert s.llm_provider is LLMProvider.openai
    assert isinstance(s.openai_api_key, SecretStr)
    assert s.openai_api_key.get_secret_value() == "sk-test-123"


def test_invalid_provider_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "not-a-provider")
    with pytest.raises(ValidationError):
        Settings()


def test_require_llm_key_missing_raises() -> None:
    s = Settings(llm_provider=LLMProvider.gemini)
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        s.require_llm_key()


def test_require_llm_key_returns_key() -> None:
    s = Settings(llm_provider=LLMProvider.gemini, gemini_api_key=SecretStr("the-key"))
    assert s.require_llm_key().get_secret_value() == "the-key"


def test_require_llm_key_ollama_raises() -> None:
    s = Settings(llm_provider=LLMProvider.ollama)
    with pytest.raises(ConfigError, match="ollama"):
        s.require_llm_key()


def test_api_key_for_provider_maps_each() -> None:
    base = Settings(
        gemini_api_key=SecretStr("g"),
        openai_api_key=SecretStr("o"),
        anthropic_api_key=SecretStr("a"),
    )
    for provider, expected in (
        (LLMProvider.gemini, "g"),
        (LLMProvider.openai, "o"),
        (LLMProvider.anthropic, "a"),
    ):
        s = base.model_copy(update={"llm_provider": provider})
        key = s.api_key_for_provider()
        assert key is not None
        assert key.get_secret_value() == expected

    ollama = base.model_copy(update={"llm_provider": LLMProvider.ollama})
    assert ollama.api_key_for_provider() is None


def test_load_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    s = load_settings()
    assert isinstance(s, Settings)
    assert s.llm_provider is LLMProvider.anthropic
