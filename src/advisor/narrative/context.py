"""Builds the read-only, JSON-safe view the LLM is allowed to see.

This is the trust boundary: it is derived solely from ``Facts`` (which carries
no raw inputs) and so structurally cannot contain raw line items, labels, or
cell references. Decimals become strings for lossless, golden-stable output.
"""

from __future__ import annotations

import json
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from advisor.schema import Facts, PeriodKPIs


def _s(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _kpi_row(k: PeriodKPIs) -> dict[str, str | None]:
    return {
        "period": k.period.label,
        "revenue": str(k.revenue),
        "cogs": str(k.cogs),
        "gross_profit": str(k.gross_profit),
        "total_opex": str(k.total_opex),
        "operating_profit": str(k.operating_profit),
        "net_profit": str(k.net_profit),
        "gross_margin_pct": _s(k.gross_margin_pct),
        "operating_margin_pct": _s(k.operating_margin_pct),
        "net_margin_pct": _s(k.net_margin_pct),
        "finance_cost_to_sales_pct": _s(k.finance_cost_to_sales_pct),
        "opex_to_sales_pct": _s(k.opex_to_sales_pct),
        "volume_mt": _s(k.volume_mt),
        "selling_price_per_mt": _s(k.selling_price_per_mt),
    }


class NarrativeContext(BaseModel):
    """The only data the LLM sees, derived purely from Facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    company_name: str
    group_name: str
    currency: str
    volume_unit: str
    period_labels: list[str]
    latest_period: str
    kpis: list[dict[str, str | None]]
    statuses: list[dict[str, str | None]]
    variances: list[dict[str, str | None]]
    anomalies: list[dict[str, str | None]]

    def as_prompt_block(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, indent=2)


def build_context(facts: Facts) -> NarrativeContext:
    """Project Facts into a prompt-safe context (pure; reads only Facts)."""
    return NarrativeContext(
        company_name=facts.entity.company_name,
        group_name=facts.entity.group_name,
        currency=facts.entity.currency,
        volume_unit=facts.entity.volume_unit,
        period_labels=[p.label for p in facts.periods],
        latest_period=facts.latest_period.label,
        kpis=[_kpi_row(k) for k in facts.kpis],
        statuses=[
            {
                "metric": s.metric,
                "period": s.period,
                "value": _s(s.value),
                "status": s.status.value,
                "message_code": s.message_code,
            }
            for s in facts.statuses
        ],
        variances=[
            {
                "metric": v.metric,
                "basis": v.basis.value,
                "from_period": v.from_period,
                "to_period": v.to_period,
                "pct_change": _s(v.pct_change),
                "bps_change": _s(v.bps_change),
                "direction": v.direction.value,
            }
            for v in facts.variances
        ],
        anomalies=[
            {
                "code": a.code,
                "severity": a.severity.value,
                "period": a.period,
                "metric": a.metric,
                "observed": _s(a.observed),
                "threshold": _s(a.threshold),
                "message_code": a.message_code,
            }
            for a in facts.anomalies
        ],
    )
