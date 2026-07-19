"""Build the JSON payload that feeds the Chart.js dashboard (M7).

Deterministic: Decimals serialized as strings, periods aligned across series,
no wall-clock (caller passes ``generated_at``).
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from advisor.narrative.advisor import Advisory
from advisor.schema import Facts

from .formatting import DISCLAIMER, status_hex


def _s(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def build_dashboard_payload(
    facts: Facts, narrative: Advisory, *, generated_at: datetime
) -> dict[str, Any]:
    labels = [p.label for p in facts.periods]
    latest = facts.latest_period.label
    scorecard = [
        {
            "metric": s.metric,
            "value": _s(s.value),
            "status": s.status.value,
            "color": status_hex(s.status),
            "message_code": s.message_code,
        }
        for s in facts.statuses
        if s.period == latest
    ]
    charts = {
        "margin_trend": {
            "labels": labels,
            "datasets": [
                {"label": "Gross margin %", "data": [_s(k.gross_margin_pct) for k in facts.kpis]},
                {
                    "label": "Operating margin %",
                    "data": [_s(k.operating_margin_pct) for k in facts.kpis],
                },
                {"label": "Net margin %", "data": [_s(k.net_margin_pct) for k in facts.kpis]},
            ],
        },
        "revenue": {
            "labels": labels,
            "data": [_s(k.revenue) for k in facts.kpis],
        },
    }
    return {
        "schema_version": facts.schema_version,
        "engine_version": facts.engine_version,
        "generated_at": generated_at.isoformat(),
        "entity": {
            "company_name": facts.entity.company_name,
            "group_name": facts.entity.group_name,
            "currency": facts.entity.currency,
            "volume_unit": facts.entity.volume_unit,
        },
        "periods": labels,
        "latest_period": latest,
        "scorecard": scorecard,
        "kpis": [k.model_dump(mode="json") for k in facts.kpis],
        "variances": [v.model_dump(mode="json") for v in facts.variances],
        "statuses": [s.model_dump(mode="json") for s in facts.statuses],
        "anomalies": [a.model_dump(mode="json") for a in facts.anomalies],
        "charts": charts,
        "narrative": {
            "executive_summary": narrative.executive_summary,
            "risk_commentary": narrative.risk_commentary,
            "recommendations": narrative.recommendations,
            "disclaimer": DISCLAIMER,
            "provider": narrative.provider,
            "model": narrative.model,
            "degraded": narrative.degraded,
        },
    }


def write_dashboard_json(
    facts: Facts, narrative: Advisory, path: Path, *, generated_at: datetime
) -> Path:
    payload = build_dashboard_payload(facts, narrative, generated_at=generated_at)
    path.write_text(
        json.dumps(payload, sort_keys=False, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    return path
