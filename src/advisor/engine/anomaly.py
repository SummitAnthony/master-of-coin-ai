"""Rule-based anomaly detection emitting stable codes + numeric context (pure).

Rules are driven by the ``anomalies`` section of ``config/thresholds.yaml``.
Growth percentages reuse the same denominator guard as variance, so anomaly
numbers agree with the Variance table. No prose is ever produced.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final

from advisor.schema import Anomaly, AnomalySeverity, PeriodKPIs, VarianceBasis

from .kpis import kpi_value
from .rounding import PCT_QUANT

MARGIN_METRICS: Final[tuple[str, ...]] = (
    "gross_margin_pct",
    "operating_margin_pct",
    "net_margin_pct",
)
COST_METRICS: Final[tuple[str, ...]] = ("cogs", "total_opex", "finance_cost")

_BPS_QUANT: Final[Decimal] = Decimal("0.01")
_SEVERITY_RANK: Final[dict[AnomalySeverity, int]] = {
    AnomalySeverity.CRITICAL: 0,
    AnomalySeverity.WARNING: 1,
    AnomalySeverity.INFO: 2,
}


def _growth(prev: Decimal | None, curr: Decimal | None) -> Decimal | None:
    """Percentage growth from prev to curr, or None if prev is missing/<= 0."""
    if prev is None or prev <= 0 or curr is None:
        return None
    return ((curr - prev) / prev * 100).quantize(PCT_QUANT, rounding=ROUND_HALF_UP)


def _anomaly(
    code: str,
    severity: AnomalySeverity,
    period: str,
    metric: str | None,
    observed: Decimal,
    threshold: Decimal,
    context: dict[str, Decimal],
) -> Anomaly:
    return Anomaly(
        code=code,
        severity=severity,
        period=period,
        basis=VarianceBasis.SEQUENTIAL,
        metric=metric,
        observed=observed,
        threshold=threshold,
        context=dict(sorted(context.items())),
        message_code=f"{code}.{severity.value}",
    )


def check_cogs_outpacing_sales(
    prev: PeriodKPIs, curr: PeriodKPIs, gap_pct: Decimal
) -> Anomaly | None:
    sales_growth = _growth(prev.revenue, curr.revenue)
    cogs_growth = _growth(prev.cogs, curr.cogs)
    if sales_growth is None or cogs_growth is None:
        return None
    gap = (cogs_growth - sales_growth).quantize(PCT_QUANT, rounding=ROUND_HALF_UP)
    if gap <= gap_pct:
        return None
    return _anomaly(
        "cogs_outpacing_sales",
        AnomalySeverity.WARNING,
        curr.period.label,
        "cogs",
        gap,
        gap_pct,
        {"cogs_growth_pct": cogs_growth, "sales_growth_pct": sales_growth, "gap_pct": gap},
    )


def check_margin_drop(prev: PeriodKPIs, curr: PeriodKPIs, max_drop_bps: Decimal) -> list[Anomaly]:
    out: list[Anomaly] = []
    for metric in MARGIN_METRICS:
        prev_v = kpi_value(prev, metric)
        curr_v = kpi_value(curr, metric)
        if prev_v is None or curr_v is None:
            continue
        drop_bps = ((prev_v - curr_v) * 100).quantize(_BPS_QUANT, rounding=ROUND_HALF_UP)
        if drop_bps > max_drop_bps:
            out.append(
                _anomaly(
                    "margin_drop",
                    AnomalySeverity.WARNING,
                    curr.period.label,
                    metric,
                    drop_bps,
                    max_drop_bps,
                    {"prev_pct": prev_v, "curr_pct": curr_v, "drop_bps": drop_bps},
                )
            )
    return out


def check_cost_spikes(prev: PeriodKPIs, curr: PeriodKPIs, spike_pct: Decimal) -> list[Anomaly]:
    out: list[Anomaly] = []
    for metric in COST_METRICS:
        growth = _growth(kpi_value(prev, metric), kpi_value(curr, metric))
        if growth is not None and growth > spike_pct:
            out.append(
                _anomaly(
                    "cost_spike",
                    AnomalySeverity.WARNING,
                    curr.period.label,
                    metric,
                    growth,
                    spike_pct,
                    {"growth_pct": growth},
                )
            )
    return out


def detect_anomalies(kpis: Sequence[PeriodKPIs], thresholds: Mapping[str, Any]) -> list[Anomaly]:
    """Run all configured anomaly rules over adjacent period pairs."""
    cfg = thresholds.get("anomalies", {})
    seq = {k.period.label: k.period.sequence for k in kpis}
    out: list[Anomaly] = []
    for i in range(len(kpis) - 1):
        prev, curr = kpis[i], kpis[i + 1]
        if "cogs_vs_sales_growth_gap_pct" in cfg:
            found = check_cogs_outpacing_sales(
                prev, curr, Decimal(str(cfg["cogs_vs_sales_growth_gap_pct"]))
            )
            if found is not None:
                out.append(found)
        if "margin_drop_bps" in cfg:
            out.extend(check_margin_drop(prev, curr, Decimal(str(cfg["margin_drop_bps"]))))
        if "cost_spike_pct" in cfg:
            out.extend(check_cost_spikes(prev, curr, Decimal(str(cfg["cost_spike_pct"]))))
    out.sort(key=lambda a: (seq[a.period], _SEVERITY_RANK[a.severity], a.code, a.metric or ""))
    return out
