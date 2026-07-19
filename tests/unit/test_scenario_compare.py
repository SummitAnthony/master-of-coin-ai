"""Tests for compare_facts branch behaviour (None and zero base values)."""

from __future__ import annotations

from decimal import Decimal

from advisor.engine.facts import build_facts
from advisor.engine.scenario import apply_scenario, compare_facts
from advisor.schema import (
    AssumptionDelta,
    DeltaOp,
    DeltaTarget,
    IncomeStatement,
    OperatingExpenses,
    Period,
    PeriodMeta,
    PeriodType,
    Scenario,
)

D = Decimal
THRESHOLDS = {
    "margins": {"gross_margin_pct": {"green": 18, "yellow": 12, "direction": "higher_is_better"}},
    "ratios": {},
    "anomalies": {},
}


def _period(label: str, **over: object) -> Period:
    data: dict[str, object] = {
        "meta": PeriodMeta(label=label, period_type=PeriodType.YEAR, fiscal_year=2024, sequence=0),
        "revenue": D("1000"),
        "cogs": D("600"),
    }
    data.update(over)
    return Period.model_validate(data)


def test_compare_handles_none_metric() -> None:
    facts = build_facts(
        IncomeStatement(periods=[_period("P", volume_mt=None)]), thresholds=THRESHOLDS
    )
    comp = compare_facts(facts, facts, "x")
    sp = next(m for m in comp.metric_deltas if m.metric == "selling_price_per_mt")
    assert sp.base_value is None
    assert sp.absolute_change is None
    assert sp.pct_change is None


def test_compare_handles_zero_base() -> None:
    # operating profit 0 -> operating_margin_pct base value is 0.
    stmt = IncomeStatement(periods=[_period("P", opex=OperatingExpenses(total=D("400")))])
    base = build_facts(stmt, thresholds=THRESHOLDS)
    scenario = build_facts(
        apply_scenario(
            stmt,
            Scenario(
                name="s",
                deltas=[
                    AssumptionDelta(target=DeltaTarget.REVENUE, op=DeltaOp.PCT, magnitude=D("10"))
                ],
            ),
        ),
        thresholds=THRESHOLDS,
    )
    comp = compare_facts(base, scenario, "s")
    om = next(m for m in comp.metric_deltas if m.metric == "operating_margin_pct")
    assert om.base_value == D("0.0000")
    assert om.pct_change is None  # base == 0
    assert om.absolute_change is not None


def test_compare_skips_unmatched_period() -> None:
    a = build_facts(IncomeStatement(periods=[_period("LABEL_A")]), thresholds=THRESHOLDS)
    b = build_facts(IncomeStatement(periods=[_period("LABEL_B")]), thresholds=THRESHOLDS)
    assert compare_facts(a, b, "x").metric_deltas == []
