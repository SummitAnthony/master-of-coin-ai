"""Tests for per-period KPI computation (full reported vs derived, guards)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from advisor.engine.kpis import KPI_METRICS, compute_period_kpis, kpi_value
from advisor.schema import LineItem, OperatingExpenses, Period, PeriodMeta, PeriodType


def _meta(label: str = "FY2023-24") -> PeriodMeta:
    return PeriodMeta(label=label, period_type=PeriodType.YEAR, fiscal_year=2024, sequence=0)


def test_full_reported_period_uses_reported_values() -> None:
    period = Period(
        meta=_meta(),
        revenue=Decimal("1000"),
        cogs=Decimal("600"),
        gross_profit=Decimal("400"),
        opex=OperatingExpenses(
            selling_distribution=Decimal("60"),
            administrative=Decimal("30"),
            other_opex=Decimal("10"),
            total=Decimal("100"),
        ),
        operating_profit=Decimal("300"),
        other_income=Decimal("20"),
        finance_cost=Decimal("50"),
        profit_before_tax=Decimal("270"),
        tax_expense=Decimal("70"),
        net_profit=Decimal("200"),
        volume_mt=Decimal("10"),
    )
    k = compute_period_kpis(period)
    assert k.gross_profit == Decimal("400.00")
    assert k.total_opex == Decimal("100.00")
    assert k.operating_profit == Decimal("300.00")
    assert k.net_profit == Decimal("200.00")
    assert k.gross_margin_pct == Decimal("40.0000")
    assert k.net_margin_pct == Decimal("20.0000")
    assert k.finance_cost_to_sales_pct == Decimal("5.0000")
    assert k.selling_price_per_mt == Decimal("100.00")
    assert k.cogs_per_mt == Decimal("60.00")
    assert k.expense_ratios_pct == {
        "administrative": Decimal("3.0000"),
        "other_opex": Decimal("1.0000"),
        "selling_distribution": Decimal("6.0000"),
    }


def test_minimal_period_derives_subtotals() -> None:
    period = Period(meta=_meta(), revenue=Decimal("1000"), cogs=Decimal("600"))
    k = compute_period_kpis(period)
    assert k.gross_profit == Decimal("400.00")  # revenue - cogs
    assert k.total_opex == Decimal("0.00")
    assert k.operating_profit == Decimal("400.00")  # gross - opex
    assert k.profit_before_tax == Decimal("400.00")
    assert k.net_profit == Decimal("400.00")
    assert k.volume_mt is None
    assert k.selling_price_per_mt is None
    assert k.expense_ratios_pct == {}


def test_total_opex_from_categories_when_no_total() -> None:
    period = Period(
        meta=_meta(),
        revenue=Decimal("1000"),
        cogs=Decimal("600"),
        opex=OperatingExpenses(
            selling_distribution=Decimal("60"),
            administrative=Decimal("30"),
            other_opex=Decimal("10"),
        ),
    )
    assert compute_period_kpis(period).total_opex == Decimal("100.00")


def test_total_opex_from_items_when_no_categories() -> None:
    period = Period(
        meta=_meta(),
        revenue=Decimal("1000"),
        cogs=Decimal("600"),
        opex=OperatingExpenses(
            items=[
                LineItem(label="Rent", amount=Decimal("70")),
                LineItem(label="Utilities", amount=Decimal("30")),
            ]
        ),
    )
    assert compute_period_kpis(period).total_opex == Decimal("100.00")


def test_zero_revenue_yields_none_ratios() -> None:
    # A category is present but revenue is 0, so its expense ratio is dropped.
    period = Period(
        meta=_meta(),
        revenue=Decimal("0"),
        cogs=Decimal("0"),
        opex=OperatingExpenses(administrative=Decimal("50")),
    )
    k = compute_period_kpis(period)
    assert k.gross_margin_pct is None
    assert k.cogs_to_sales_pct is None
    assert k.expense_ratios_pct == {}


def test_kpi_value_accessor_and_unknown_metric() -> None:
    period = Period(meta=_meta(), revenue=Decimal("1000"), cogs=Decimal("600"))
    k = compute_period_kpis(period)
    assert kpi_value(k, "revenue") == Decimal("1000.00")
    assert "gross_margin_pct" in KPI_METRICS
    with pytest.raises(KeyError):
        kpi_value(k, "not_a_metric")
