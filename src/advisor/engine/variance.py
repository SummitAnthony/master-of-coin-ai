"""Multi-period variance on each basis the period grid supports (pure)."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from advisor.schema import PeriodKPIs, PeriodMeta, PeriodType, Variance, VarianceBasis

from .kpis import kpi_value
from .rounding import MONEY_QUANT, PCT_QUANT, direction_of

DEFAULT_VARIANCE_METRICS: Final[tuple[str, ...]] = (
    "revenue",
    "cogs",
    "gross_profit",
    "total_opex",
    "operating_profit",
    "net_profit",
    "volume_mt",
    "gross_margin_pct",
    "operating_margin_pct",
    "net_margin_pct",
    "finance_cost_to_sales_pct",
    "opex_to_sales_pct",
    "selling_price_per_mt",
    "cogs_per_mt",
)

VARIANCE_BASES: Final[tuple[VarianceBasis, ...]] = (
    VarianceBasis.SEQUENTIAL,
    VarianceBasis.MOM,
    VarianceBasis.QOQ,
    VarianceBasis.YOY,
)

_BPS_QUANT: Final[Decimal] = Decimal("0.01")


def period_pairs(periods: Sequence[PeriodMeta], basis: VarianceBasis) -> list[tuple[int, int]]:
    """Return (from_idx, to_idx) pairs (into the sequence-ordered list)."""
    n = len(periods)
    if basis is VarianceBasis.SEQUENTIAL:
        return [(i, i + 1) for i in range(n - 1)]
    if basis is VarianceBasis.MOM:
        return [
            (i, i + 1)
            for i in range(n - 1)
            if periods[i].period_type is PeriodType.MONTH
            and periods[i + 1].period_type is PeriodType.MONTH
        ]
    if basis is VarianceBasis.QOQ:
        return [
            (i, i + 1)
            for i in range(n - 1)
            if periods[i].period_type is PeriodType.QUARTER
            and periods[i + 1].period_type is PeriodType.QUARTER
        ]
    # YOY: same period_type, to.fiscal_year == from.fiscal_year + 1, sub_index matched.
    pairs: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(n):
            a, b = periods[i], periods[j]
            if a.period_type is not b.period_type:
                continue
            if b.fiscal_year != a.fiscal_year + 1:
                continue
            if a.period_type is PeriodType.YEAR or (
                a.sub_index is not None and a.sub_index == b.sub_index
            ):
                pairs.append((i, j))
    return pairs


def compute_variance(
    metric: str, basis: VarianceBasis, from_kpis: PeriodKPIs, to_kpis: PeriodKPIs
) -> Variance:
    """Compute the change in ``metric`` from one period's KPIs to another's."""
    from_value = kpi_value(from_kpis, metric)
    to_value = kpi_value(to_kpis, metric)
    is_pct = metric.endswith("_pct")

    absolute: Decimal | None = None
    pct_change: Decimal | None = None
    bps_change: Decimal | None = None

    if from_value is not None and to_value is not None:
        quant = PCT_QUANT if is_pct else MONEY_QUANT
        absolute = (to_value - from_value).quantize(quant, rounding=ROUND_HALF_UP)
        if is_pct:
            bps_change = (absolute * 100).quantize(_BPS_QUANT, rounding=ROUND_HALF_UP)

    if from_value is not None and from_value > 0 and to_value is not None:
        pct_change = ((to_value - from_value) / from_value * 100).quantize(
            PCT_QUANT, rounding=ROUND_HALF_UP
        )

    return Variance(
        metric=metric,
        basis=basis,
        from_period=from_kpis.period.label,
        to_period=to_kpis.period.label,
        from_value=from_value,
        to_value=to_value,
        absolute_change=absolute,
        pct_change=pct_change,
        bps_change=bps_change,
        direction=direction_of(absolute),
    )


def compute_all_variances(
    kpis: Sequence[PeriodKPIs],
    periods: Sequence[PeriodMeta],
    metrics: Sequence[str] = DEFAULT_VARIANCE_METRICS,
    bases: Sequence[VarianceBasis] = VARIANCE_BASES,
) -> list[Variance]:
    """All computable variances, ordered by basis, then metric, then pair.

    A pair where both endpoints are missing the metric is skipped.
    """
    out: list[Variance] = []
    for basis in bases:
        pairs = period_pairs(periods, basis)
        for metric in metrics:
            for i, j in pairs:
                variance = compute_variance(metric, basis, kpis[i], kpis[j])
                if variance.from_value is None and variance.to_value is None:
                    continue
                out.append(variance)
    return out
