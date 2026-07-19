"""Assemble the frozen Facts object from an IncomeStatement (pure)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from advisor.config import load_thresholds
from advisor.schema import Facts, IncomeStatement

from .anomaly import detect_anomalies
from .kpis import compute_period_kpis
from .status import evaluate_all_statuses
from .variance import compute_all_variances

ENGINE_VERSION: Final[str] = "aopl-engine/1.0"


def build_facts(
    statement: IncomeStatement, *, thresholds: Mapping[str, Any] | None = None
) -> Facts:
    """Compute the full, reproducible Facts graph for a statement.

    Pure and offline. ``thresholds`` defaults to ``config/thresholds.yaml``;
    tests always pass an explicit dict for determinism.
    """
    if thresholds is None:
        thresholds = load_thresholds()

    metas = [period.meta for period in statement.periods]
    kpis = [compute_period_kpis(period) for period in statement.periods]
    refs = [period_kpis.period for period_kpis in kpis]

    return Facts(
        engine_version=ENGINE_VERSION,
        entity=statement.entity,
        periods=refs,
        latest_period=refs[-1],
        kpis=kpis,
        variances=compute_all_variances(kpis, metas),
        statuses=evaluate_all_statuses(kpis, thresholds),
        anomalies=detect_anomalies(kpis, thresholds),
    )
