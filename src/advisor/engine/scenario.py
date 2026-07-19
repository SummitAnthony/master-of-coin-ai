"""Pure, deterministic what-if/scenario engine.

Applies assumption deltas to a canonical ``IncomeStatement`` (the base is never
mutated), re-runs the M2 facts builder, and produces a structured base-vs-
scenario comparison. No network/LLM/narrative imports.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final

from advisor.schema import (
    AssumptionDelta,
    DeltaOp,
    DeltaTarget,
    Facts,
    IncomeStatement,
    MetricDelta,
    Period,
    Scenario,
    ScenarioComparison,
    ScenarioResult,
)

from .facts import build_facts
from .kpis import kpi_value
from .rounding import MONEY_QUANT, PCT_QUANT, direction_of

_TARGET_FIELD: Final[dict[DeltaTarget, str]] = {
    DeltaTarget.REVENUE: "revenue",
    DeltaTarget.COGS: "cogs",
    DeltaTarget.FINANCE_COST: "finance_cost",
    DeltaTarget.OTHER_INCOME: "other_income",
    DeltaTarget.TAX_EXPENSE: "tax_expense",
}
_OPEX_FIELD: Final[dict[DeltaTarget, str]] = {
    DeltaTarget.OPEX_ADMINISTRATIVE: "administrative",
    DeltaTarget.OPEX_SELLING_DISTRIBUTION: "selling_distribution",
    DeltaTarget.OPEX_OTHER: "other_opex",
}
_NONNEG_FIELDS: Final[frozenset[str]] = frozenset({"revenue", "cogs", "finance_cost"})
_DERIVED_FIELDS: Final[tuple[str, ...]] = (
    "gross_profit",
    "operating_profit",
    "profit_before_tax",
    "net_profit",
)
COMPARE_METRICS: Final[tuple[str, ...]] = (
    "revenue",
    "gross_margin_pct",
    "operating_margin_pct",
    "net_margin_pct",
    "net_profit",
    "selling_price_per_mt",
    "gross_profit_per_mt",
)


class ScenarioError(ValueError):
    """Raised when a scenario transform is invalid (e.g. drives a value negative)."""


def _transform_value(current: Decimal, op: DeltaOp, magnitude: Decimal) -> Decimal:
    if op is DeltaOp.PCT:
        return current * (Decimal(1) + magnitude / Decimal(100))
    if op is DeltaOp.ABSOLUTE:
        return current + magnitude
    return magnitude  # SET


def _clear_derived(data: dict[str, Any]) -> None:
    for field in _DERIVED_FIELDS:
        data[field] = None


def _apply_delta_to_period(period: Period, delta: AssumptionDelta) -> Period:
    data = period.model_dump()
    label = period.meta.label
    target = delta.target

    if target in _TARGET_FIELD:
        field = _TARGET_FIELD[target]
        base = data[field] if data[field] is not None else Decimal(0)
        new_value = _transform_value(base, delta.op, delta.magnitude)
        if field in _NONNEG_FIELDS and new_value < 0:
            raise ScenarioError(
                f"{target.value} for period '{label}' would be negative ({new_value})"
            )
        data[field] = new_value
    elif target is DeltaTarget.PRICE_PER_MT:
        revenue = data["revenue"]
        volume = data["volume_mt"]
        if delta.op is DeltaOp.PCT:
            new_revenue = _transform_value(revenue, DeltaOp.PCT, delta.magnitude)
        else:
            if volume is None:
                raise ScenarioError(
                    f"price_per_mt {delta.op.value} needs volume for period '{label}'"
                )
            new_revenue = (
                revenue + delta.magnitude * volume
                if delta.op is DeltaOp.ABSOLUTE
                else delta.magnitude * volume
            )
        if new_revenue < 0:
            raise ScenarioError(f"revenue for period '{label}' would be negative ({new_revenue})")
        data["revenue"] = new_revenue
    elif target is DeltaTarget.VOLUME:
        volume = data["volume_mt"]
        if delta.op is DeltaOp.SET:
            new_volume = delta.magnitude
        else:
            if volume is None:
                raise ScenarioError(
                    f"volume {delta.op.value} needs existing volume for period '{label}'"
                )
            new_volume = _transform_value(volume, delta.op, delta.magnitude)
        if new_volume < 0:
            raise ScenarioError(f"volume for period '{label}' would be negative ({new_volume})")
        data["volume_mt"] = new_volume
    else:  # opex category
        field = _OPEX_FIELD[target]
        base = data["opex"][field] if data["opex"][field] is not None else Decimal(0)
        new_value = _transform_value(base, delta.op, delta.magnitude)
        if new_value < 0:
            raise ScenarioError(
                f"{target.value} for period '{label}' would be negative ({new_value})"
            )
        data["opex"][field] = new_value
        data["opex"]["total"] = None

    _clear_derived(data)
    return Period.model_validate(data)


def apply_scenario(statement: IncomeStatement, scenario: Scenario) -> IncomeStatement:
    """Return a NEW statement with deltas applied in order; base never mutated."""
    labels = {p.meta.label for p in statement.periods}
    periods: list[Period] = [p.model_copy(deep=True) for p in statement.periods]
    for delta in scenario.deltas:
        if delta.applies_to is not None and delta.applies_to not in labels:
            raise ScenarioError(
                f"applies_to '{delta.applies_to}' is not a period label; "
                f"valid labels: {sorted(labels)}"
            )
        periods = [
            _apply_delta_to_period(period, delta)
            if (delta.applies_to is None or period.meta.label == delta.applies_to)
            else period
            for period in periods
        ]
    return IncomeStatement(
        schema_version=statement.schema_version,
        entity=statement.entity,
        periods=periods,
        source=statement.source,
    )


def compare_facts(base: Facts, scenario: Facts, scenario_name: str) -> ScenarioComparison:
    """Per-period, per-KPI structured diff, ordered by period sequence then metric."""
    scen_by_label = {k.period.label: k for k in scenario.kpis}
    deltas: list[MetricDelta] = []
    for base_kpis in sorted(base.kpis, key=lambda k: k.period.sequence):
        scen_kpis = scen_by_label.get(base_kpis.period.label)
        if scen_kpis is None:
            continue
        for metric in COMPARE_METRICS:
            base_value = kpi_value(base_kpis, metric)
            scenario_value = kpi_value(scen_kpis, metric)
            quant = PCT_QUANT if metric.endswith("_pct") else MONEY_QUANT
            absolute: Decimal | None = None
            if base_value is not None and scenario_value is not None:
                absolute = (scenario_value - base_value).quantize(quant, rounding=ROUND_HALF_UP)
            pct_change: Decimal | None = None
            if base_value is not None and base_value != 0 and scenario_value is not None:
                pct_change = ((scenario_value - base_value) / base_value * 100).quantize(
                    PCT_QUANT, rounding=ROUND_HALF_UP
                )
            deltas.append(
                MetricDelta(
                    metric=metric,
                    period=base_kpis.period.label,
                    base_value=base_value,
                    scenario_value=scenario_value,
                    absolute_change=absolute,
                    pct_change=pct_change,
                    direction=direction_of(absolute),
                )
            )
    return ScenarioComparison(scenario_name=scenario_name, metric_deltas=deltas)


def run_scenario(
    statement: IncomeStatement,
    scenario: Scenario,
    thresholds: Mapping[str, Any] | None = None,
) -> ScenarioResult:
    """Apply a scenario, build base + scenario Facts, and compare them."""
    scenario_statement = apply_scenario(statement, scenario)
    base_facts = build_facts(statement, thresholds=thresholds)
    scenario_facts = build_facts(scenario_statement, thresholds=thresholds)
    return ScenarioResult(
        scenario=scenario,
        base_facts=base_facts,
        scenario_facts=scenario_facts,
        comparison=compare_facts(base_facts, scenario_facts, scenario.name),
    )
