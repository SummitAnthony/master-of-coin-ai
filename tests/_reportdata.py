"""Shared builders for report tests (not a pytest fixture file)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from advisor.engine.facts import build_facts
from advisor.narrative.advisor import Advisory
from advisor.schema import (
    Facts,
    IncomeStatement,
    OperatingExpenses,
    Period,
    PeriodMeta,
    PeriodType,
)

D = Decimal
GEN_AT = datetime(2024, 6, 30, 9, 0, 0)
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


def make_facts() -> Facts:
    stmt = IncomeStatement(
        periods=[
            Period(
                meta=PeriodMeta(
                    label="FY2022-23", period_type=PeriodType.YEAR, fiscal_year=2023, sequence=0
                ),
                revenue=D("2000000000"),
                cogs=D("1200000000"),
                opex=OperatingExpenses(
                    administrative=D("100000000"),
                    selling_distribution=D("80000000"),
                    other_opex=D("20000000"),
                ),
                finance_cost=D("60000000"),
                volume_mt=D("16000"),
            ),
            Period(
                meta=PeriodMeta(
                    label="FY2023-24", period_type=PeriodType.YEAR, fiscal_year=2024, sequence=1
                ),
                revenue=D("2480000000"),
                cogs=D("1910000000"),
                opex=OperatingExpenses(
                    administrative=D("138000000"),
                    selling_distribution=D("96000000"),
                    other_opex=D("22000000"),
                ),
                finance_cost=D("142000000"),
                volume_mt=D("18500"),
            ),
        ]
    )
    return build_facts(stmt, thresholds=THRESHOLDS)


def make_advisory() -> Advisory:
    return Advisory(
        executive_summary="AOPL revenue grew while margins compressed under higher input costs.",
        risk_commentary="Gross margin slipped and finance cost rose relative to sales.",
        recommendations=["Renegotiate raw material contracts.", "Review debt structure."],
        provider="mock",
        model="mock-model",
        degraded=False,
    )
