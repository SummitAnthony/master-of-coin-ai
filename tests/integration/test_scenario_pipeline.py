"""Integration tests for run_scenario: the full apply -> build -> compare pipeline."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from advisor.engine.facts import build_facts
from advisor.engine.scenario import compare_facts, run_scenario
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
    Status,
)

D = Decimal
THRESHOLDS = {
    "margins": {
        "gross_margin_pct": {"green": 18, "yellow": 12, "direction": "higher_is_better"},
        "operating_margin_pct": {"green": 10, "yellow": 5, "direction": "higher_is_better"},
        "net_margin_pct": {"green": 6, "yellow": 2, "direction": "higher_is_better"},
    },
    "ratios": {
        "finance_cost_to_sales_pct": {"green": 3, "yellow": 6, "direction": "lower_is_better"}
    },
    "anomalies": {
        "margin_drop_bps": 200,
        "cogs_vs_sales_growth_gap_pct": 3.0,
        "cost_spike_pct": 15.0,
    },
}


def _stmt() -> IncomeStatement:
    return IncomeStatement(
        periods=[
            Period(
                meta=PeriodMeta(
                    label="FY2023-24", period_type=PeriodType.YEAR, fiscal_year=2024, sequence=0
                ),
                revenue=D("1000"),
                cogs=D("600"),
                opex=OperatingExpenses(
                    administrative=D("50"),
                    selling_distribution=D("30"),
                    other_opex=D("20"),
                ),
                finance_cost=D("40"),
                other_income=D("10"),
                tax_expense=D("20"),
                volume_mt=D("100"),
            )
        ]
    )


def _scenario(target: DeltaTarget, op: DeltaOp, mag: str) -> Scenario:
    return Scenario(
        name="what-if", deltas=[AssumptionDelta(target=target, op=op, magnitude=D(mag))]
    )


def test_base_facts_match_direct_build() -> None:
    result = run_scenario(
        _stmt(), _scenario(DeltaTarget.COGS, DeltaOp.PCT, "8"), thresholds=THRESHOLDS
    )
    assert result.base_facts == build_facts(_stmt(), thresholds=THRESHOLDS)


def test_cogs_increase_lowers_gross_margin() -> None:
    result = run_scenario(
        _stmt(), _scenario(DeltaTarget.COGS, DeltaOp.PCT, "8"), thresholds=THRESHOLDS
    )
    base_gm = result.base_facts.kpis[0].gross_margin_pct
    scen_gm = result.scenario_facts.kpis[0].gross_margin_pct
    assert base_gm is not None and scen_gm is not None
    assert scen_gm < base_gm


def test_run_scenario_is_deterministic() -> None:
    s = _scenario(DeltaTarget.REVENUE, DeltaOp.PCT, "-10")
    a = run_scenario(_stmt(), s, thresholds=THRESHOLDS)
    b = run_scenario(_stmt(), s, thresholds=THRESHOLDS)
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_base_statement_unchanged_after_run() -> None:
    stmt = _stmt()
    snapshot = stmt.model_dump()
    run_scenario(stmt, _scenario(DeltaTarget.COGS, DeltaOp.PCT, "8"), thresholds=THRESHOLDS)
    assert stmt.model_dump() == snapshot


def test_comparison_metric_deltas_present() -> None:
    result = run_scenario(
        _stmt(), _scenario(DeltaTarget.REVENUE, DeltaOp.PCT, "-10"), thresholds=THRESHOLDS
    )
    metrics = {m.metric for m in result.comparison.metric_deltas}
    assert {"revenue", "net_margin_pct"} <= metrics
    rev = next(m for m in result.comparison.metric_deltas if m.metric == "revenue")
    assert rev.absolute_change == D("-100.00")
    assert rev.pct_change == D("-10.0000")


def test_compare_facts_standalone_matches() -> None:
    result = run_scenario(
        _stmt(), _scenario(DeltaTarget.COGS, DeltaOp.PCT, "8"), thresholds=THRESHOLDS
    )
    assert compare_facts(result.base_facts, result.scenario_facts, "what-if") == result.comparison


def test_price_increase_improves_net_profit() -> None:
    result = run_scenario(
        _stmt(), _scenario(DeltaTarget.PRICE_PER_MT, DeltaOp.PCT, "5"), thresholds=THRESHOLDS
    )
    assert result.scenario_facts.kpis[0].net_profit > result.base_facts.kpis[0].net_profit


def test_status_flips_red_on_cost_spike() -> None:
    # Large COGS jump drives gross margin below the red threshold.
    result = run_scenario(
        _stmt(), _scenario(DeltaTarget.COGS, DeltaOp.PCT, "50"), thresholds=THRESHOLDS
    )
    scen_status = next(s for s in result.scenario_facts.statuses if s.metric == "gross_margin_pct")
    assert scen_status.status is Status.RED


def test_scenario_facts_are_frozen() -> None:
    result = run_scenario(
        _stmt(), _scenario(DeltaTarget.COGS, DeltaOp.PCT, "8"), thresholds=THRESHOLDS
    )
    with pytest.raises(ValidationError):
        result.scenario_facts.engine_version = "x"


def test_run_scenario_no_thresholds_defaults() -> None:
    result = run_scenario(_stmt(), _scenario(DeltaTarget.COGS, DeltaOp.PCT, "8"))
    assert result.scenario_facts.kpis[0].gross_margin_pct is not None
