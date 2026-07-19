"""Engine purity: build_facts must run with no network access."""

from __future__ import annotations

import socket
from decimal import Decimal

import pytest

from advisor.engine.facts import build_facts
from advisor.schema import IncomeStatement, Period, PeriodMeta, PeriodType

_THRESHOLDS = {
    "margins": {"gross_margin_pct": {"green": 18, "yellow": 12, "direction": "higher_is_better"}},
    "ratios": {},
    "anomalies": {},
}


def test_build_facts_runs_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("engine attempted network access")

    monkeypatch.setattr(socket, "socket", _boom)
    stmt = IncomeStatement(
        periods=[
            Period(
                meta=PeriodMeta(
                    label="FY2023-24", period_type=PeriodType.YEAR, fiscal_year=2024, sequence=0
                ),
                revenue=Decimal("1000"),
                cogs=Decimal("600"),
            )
        ]
    )
    facts = build_facts(stmt, thresholds=_THRESHOLDS)
    assert facts.latest_period.label == "FY2023-24"
