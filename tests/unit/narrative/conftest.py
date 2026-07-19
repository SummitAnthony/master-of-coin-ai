"""Shared fixtures for narrative-layer tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import SecretStr

from advisor.config import LLMProvider, Settings
from advisor.engine.facts import build_facts
from advisor.schema import (
    Facts,
    IncomeStatement,
    OperatingExpenses,
    Period,
    PeriodMeta,
    PeriodType,
)

D = Decimal

THRESHOLDS = {
    "margins": {
        "gross_margin_pct": {"green": 18, "yellow": 12, "direction": "higher_is_better"},
        "operating_margin_pct": {"green": 10, "yellow": 5, "direction": "higher_is_better"},
        "net_margin_pct": {"green": 6, "yellow": 2, "direction": "higher_is_better"},
    },
    "ratios": {
        "finance_cost_to_sales_pct": {"green": 3, "yellow": 6, "direction": "lower_is_better"}
    },
    "anomalies": {
        "margin_drop_bps": 200,
        "cogs_vs_sales_growth_gap_pct": 3.0,
        "cost_spike_pct": 15.0,
    },
}


def _period(seq: int, label: str, fy: int, rev: str, cogs: str, vol: str) -> Period:
    return Period(
        meta=PeriodMeta(label=label, period_type=PeriodType.YEAR, fiscal_year=fy, sequence=seq),
        revenue=D(rev),
        cogs=D(cogs),
        opex=OperatingExpenses(
            administrative=D("100"), selling_distribution=D("80"), other_opex=D("20")
        ),
        finance_cost=D("60"),
        volume_mt=D(vol),
    )


@pytest.fixture
def facts() -> Facts:
    stmt = IncomeStatement(
        periods=[
            _period(0, "FY2022-23", 2023, "2000", "1200", "1000"),
            _period(1, "FY2023-24", 2024, "2200", "1600", "1050"),  # cogs jump -> anomaly
        ]
    )
    return build_facts(stmt, thresholds=THRESHOLDS)


class RecordingClient:
    """A SupportsGenerate mock that records prompts and returns canned text."""

    provider = "mock"
    model = "mock-model"

    def __init__(self, responses: list[str] | None = None) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self._responses = responses or [
            "Executive summary prose.",
            "Risk commentary prose.",
            "- Recommendation one\n- Recommendation two\n- Recommendation three",
        ]

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append((prompt, system))
        return self._responses[(len(self.calls) - 1) % len(self._responses)]


@pytest.fixture
def recording_client() -> RecordingClient:
    return RecordingClient()


def settings_for(provider: LLMProvider, *, with_key: bool) -> Settings:
    kwargs: dict[str, object] = {"llm_provider": provider}
    if provider is LLMProvider.ollama:
        kwargs["ollama_base_url"] = "http://localhost:11434" if with_key else ""
    elif with_key:
        kwargs[f"{provider.value}_api_key"] = SecretStr("test-key")
    return Settings.model_validate(kwargs)
