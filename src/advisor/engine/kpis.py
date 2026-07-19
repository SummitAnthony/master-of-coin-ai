"""Resolve a Period into a fully-populated, quantized PeriodKPIs (pure)."""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from advisor.schema import OperatingExpenses, Period, PeriodKPIs, PeriodRef

from .rounding import pct_of, per_mt, quantize_money

KPI_METRICS: Final[tuple[str, ...]] = (
    "revenue",
    "cogs",
    "gross_profit",
    "total_opex",
    "operating_profit",
    "other_income",
    "finance_cost",
    "profit_before_tax",
    "tax_expense",
    "net_profit",
    "volume_mt",
    "gross_margin_pct",
    "operating_margin_pct",
    "net_margin_pct",
    "cogs_to_sales_pct",
    "opex_to_sales_pct",
    "finance_cost_to_sales_pct",
    "selling_price_per_mt",
    "cogs_per_mt",
    "gross_profit_per_mt",
)

_EXPENSE_CATEGORIES: Final[tuple[tuple[str, str], ...]] = (
    ("selling_distribution", "selling_distribution"),
    ("administrative", "administrative"),
    ("other_opex", "other_opex"),
)


def _resolve_total_opex(opex: OperatingExpenses) -> Decimal:
    if opex.total is not None:
        return opex.total
    categories = [
        c
        for c in (
            opex.selling_distribution,
            opex.administrative,
            opex.other_opex,
        )
        if c is not None
    ]
    if categories:
        return sum(categories, Decimal(0))
    if opex.items:
        return sum((item.amount for item in opex.items), Decimal(0))
    return Decimal(0)


def _expense_ratios(opex: OperatingExpenses, revenue: Decimal) -> dict[str, Decimal]:
    ratios: dict[str, Decimal] = {}
    for key, attr in _EXPENSE_CATEGORIES:
        amount = getattr(opex, attr)
        if amount is not None:
            value = pct_of(amount, revenue)
            if value is not None:
                ratios[key] = value
    return dict(sorted(ratios.items()))


def compute_period_kpis(period: Period) -> PeriodKPIs:
    """Resolve subtotals, ratios and per-MT economics for one period."""
    revenue = quantize_money(period.revenue)
    cogs = quantize_money(period.cogs)
    gross_profit = quantize_money(
        period.gross_profit if period.gross_profit is not None else revenue - cogs
    )
    total_opex = quantize_money(_resolve_total_opex(period.opex))
    operating_profit = quantize_money(
        period.operating_profit
        if period.operating_profit is not None
        else gross_profit - total_opex
    )
    other_income = quantize_money(period.other_income or Decimal(0))
    finance_cost = quantize_money(period.finance_cost or Decimal(0))
    tax = quantize_money(period.tax_expense or Decimal(0))
    pbt = quantize_money(
        period.profit_before_tax
        if period.profit_before_tax is not None
        else operating_profit + other_income - finance_cost
    )
    net = quantize_money(period.net_profit if period.net_profit is not None else pbt - tax)
    volume = period.volume_mt

    return PeriodKPIs(
        period=PeriodRef(
            label=period.meta.label,
            period_type=period.meta.period_type,
            fiscal_year=period.meta.fiscal_year,
            sequence=period.meta.sequence,
        ),
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        total_opex=total_opex,
        operating_profit=operating_profit,
        other_income=other_income,
        finance_cost=finance_cost,
        profit_before_tax=pbt,
        tax_expense=tax,
        net_profit=net,
        volume_mt=volume,
        gross_margin_pct=pct_of(gross_profit, revenue),
        operating_margin_pct=pct_of(operating_profit, revenue),
        net_margin_pct=pct_of(net, revenue),
        cogs_to_sales_pct=pct_of(cogs, revenue),
        opex_to_sales_pct=pct_of(total_opex, revenue),
        finance_cost_to_sales_pct=pct_of(finance_cost, revenue),
        selling_price_per_mt=per_mt(revenue, volume),
        cogs_per_mt=per_mt(cogs, volume),
        gross_profit_per_mt=per_mt(gross_profit, volume),
        expense_ratios_pct=_expense_ratios(period.opex, revenue),
    )


def kpi_value(kpis: PeriodKPIs, metric: str) -> Decimal | None:
    """Return a KPI value by field name; raise KeyError for an unknown metric."""
    if metric not in KPI_METRICS:
        raise KeyError(metric)
    value: Decimal | None = getattr(kpis, metric)
    return value
