"""Evaluate KPIs against user thresholds into red/yellow/green bands (pure).

Thresholds are user data from ``config/thresholds.yaml`` (sections ``margins``
and ``ratios``); they are never hardcoded.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from advisor.schema import KpiStatus, PeriodKPIs, Status, ThresholdDirection

from .kpis import kpi_value

_RULE_SECTIONS = ("margins", "ratios")


@dataclass(frozen=True)
class ThresholdRule:
    """Traffic-light bounds for one KPI."""

    metric: str
    green_at: Decimal
    yellow_at: Decimal
    direction: ThresholdDirection


def parse_threshold_rules(thresholds: Mapping[str, Any]) -> dict[str, ThresholdRule]:
    """Flatten the ``margins`` and ``ratios`` sections into per-metric rules."""
    rules: dict[str, ThresholdRule] = {}
    for section in _RULE_SECTIONS:
        metrics = thresholds.get(section, {})
        for metric, cfg in metrics.items():
            rules[metric] = ThresholdRule(
                metric=metric,
                green_at=Decimal(str(cfg["green"])),
                yellow_at=Decimal(str(cfg["yellow"])),
                direction=ThresholdDirection(cfg["direction"]),
            )
    return rules


def classify(value: Decimal | None, rule: ThresholdRule) -> Status:
    """Return the band for a value (inclusive boundaries); None -> UNKNOWN."""
    if value is None:
        return Status.UNKNOWN
    if rule.direction is ThresholdDirection.HIGHER_IS_BETTER:
        if value >= rule.green_at:
            return Status.GREEN
        if value >= rule.yellow_at:
            return Status.YELLOW
        return Status.RED
    if value <= rule.green_at:
        return Status.GREEN
    if value <= rule.yellow_at:
        return Status.YELLOW
    return Status.RED


def evaluate_status(
    metric: str, period_label: str, value: Decimal | None, rule: ThresholdRule
) -> KpiStatus:
    status = classify(value, rule)
    return KpiStatus(
        metric=metric,
        period=period_label,
        value=value,
        status=status,
        direction=rule.direction,
        green_at=rule.green_at,
        yellow_at=rule.yellow_at,
        message_code=f"{metric}.{status.value}",
    )


def evaluate_all_statuses(
    kpis: Sequence[PeriodKPIs], thresholds: Mapping[str, Any]
) -> list[KpiStatus]:
    """One status per (period, threshold-backed metric); period then metric order."""
    rules = parse_threshold_rules(thresholds)
    out: list[KpiStatus] = []
    for period_kpis in kpis:
        for metric in sorted(rules):
            out.append(
                evaluate_status(
                    metric, period_kpis.period.label, kpi_value(period_kpis, metric), rules[metric]
                )
            )
    return out
