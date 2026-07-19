"""Application settings and threshold loading.

Settings come from environment variables / a local ``.env`` (never committed).
Thresholds are user-editable data in ``config/thresholds.yaml`` and are never
baked into code.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from ._resources import resource_path
from .schema import EntityMeta

DEFAULT_THRESHOLDS_PATH = resource_path("config/thresholds.yaml")


class ConfigError(RuntimeError):
    """Raised when configuration is missing or invalid (fails loudly)."""


class LLMProvider(StrEnum):
    """Supported LLM backends, selected via the ``LLM_PROVIDER`` env var."""

    gemini = "gemini"
    openai = "openai"
    anthropic = "anthropic"
    ollama = "ollama"


class Settings(BaseSettings):
    """Runtime settings loaded from the environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: LLMProvider = LLMProvider.gemini
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Optional LLM tuning (narrative layer). llm_model overrides the per-provider default.
    llm_model: str | None = None
    llm_temperature: float = 0.0
    llm_timeout: float = 30.0

    # Company profile — all branding/reporting context is configurable per deployment.
    company_name: str = "Your Company"
    group_name: str = ""
    currency: str = "USD"
    volume_unit: str = "MT"
    fiscal_year_end_month: int = 12
    product_name: str = "Master of Coin AI"

    thresholds_path: Path = DEFAULT_THRESHOLDS_PATH

    def entity_meta(self) -> EntityMeta:
        """Project the company-profile settings onto the canonical entity model."""
        return EntityMeta(
            company_name=self.company_name,
            group_name=self.group_name,
            currency=self.currency,
            volume_unit=self.volume_unit,
            fiscal_year_end_month=self.fiscal_year_end_month,
        )

    def api_key_for_provider(self) -> SecretStr | None:
        """Return the API key for the currently selected provider, if any."""
        keys: dict[LLMProvider, SecretStr | None] = {
            LLMProvider.gemini: self.gemini_api_key,
            LLMProvider.openai: self.openai_api_key,
            LLMProvider.anthropic: self.anthropic_api_key,
            LLMProvider.ollama: None,
        }
        return keys[self.llm_provider]

    def require_llm_key(self) -> SecretStr:
        """Return the selected provider's API key, or fail loudly.

        ``ollama`` runs locally and uses ``ollama_base_url`` rather than a key,
        so requiring a key for it is itself a configuration error.
        """
        if self.llm_provider is LLMProvider.ollama:
            raise ConfigError("Provider 'ollama' uses OLLAMA_BASE_URL, not an API key.")
        key = self.api_key_for_provider()
        if key is None:
            var = f"{self.llm_provider.value.upper()}_API_KEY"
            raise ConfigError(
                f"Missing API key for provider '{self.llm_provider.value}'. "
                f"Set {var} in your .env file."
            )
        return key


def load_settings() -> Settings:
    """Construct :class:`Settings` from the environment / ``.env``."""
    return Settings()


def load_thresholds(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the thresholds YAML, failing loudly on any problem."""
    target = path if path is not None else load_settings().thresholds_path
    if not target.exists():
        raise ConfigError(f"Thresholds file not found: {target}")
    try:
        data: Any = yaml.safe_load(target.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Could not read thresholds file {target}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Thresholds file {target} must contain a top-level mapping.")
    return data
