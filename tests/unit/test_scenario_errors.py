"""Tests for ScenarioError paths in apply_scenario."""

from __future__ import annotations

from decimal import Decimal

import pytest

from advisor.engine.scenario import ScenarioError, apply_scenario
from advisor.schema import (
    AssumptionDelta,
    DeltaOp,
    DeltaTarget,
    IncomeStatement,
    Period,
    PeriodMeta,
    PeriodType,
    Scenario,
)

D = Decimal


def _period(label: str = "FY2023-24", **over: object) -> Period:
    data: dict[str, object] = {
        "meta": PeriodMeta(label=label, period_type=PeriodType.YEAR, fiscal_year=2024, sequence=0),
        "revenue": D("1000"),
        "cogs": D("600"),
    }
    data.update(over)
    return Period.model_validate(data)


def _run(
    target: DeltaTarget,
    op: DeltaOp,
    mag: str,
    period: Period | None = None,
    applies_to: str | None = None,
) -> None:
    stmt = IncomeStatement(periods=[period or _period()])
    scenario = Scenario(
        name="s",
        deltas=[AssumptionDelta(target=target, op=op, magnitude=D(mag), applies_to=applies_to)],
    )
    apply_scenario(stmt, scenario)


def test_error_is_valueerror_subclass() -> None:
    assert issubclass(ScenarioError, ValueError)


def test_revenue_driven_negative_raises() -> None:
    with pytest.raises(ScenarioError, match="revenue"):
        _run(DeltaTarget.REVENUE, DeltaOp.PCT, "-120")


def test_cogs_driven_negative_raises() -> None:
    with pytest.raises(ScenarioError, match="cogs"):
        _run(DeltaTarget.COGS, DeltaOp.SET, "-1")


def test_finance_cost_negative_raises() -> None:
    with pytest.raises(ScenarioError, match="finance_cost"):
        _run(DeltaTarget.FINANCE_COST, DeltaOp.SET, "-5", period=_period(finance_cost=D("40")))


def test_set_negative_revenue_raises() -> None:
    with pytest.raises(ScenarioError):
        _run(DeltaTarget.REVENUE, DeltaOp.SET, "-5")


def test_price_per_mt_requires_volume() -> None:
    with pytest.raises(ScenarioError, match="volume"):
        _run(DeltaTarget.PRICE_PER_MT, DeltaOp.SET, "120", period=_period(volume_mt=None))


def test_price_per_mt_driven_negative_raises() -> None:
    with pytest.raises(ScenarioError, match="revenue"):
        _run(DeltaTarget.PRICE_PER_MT, DeltaOp.ABSOLUTE, "-9999", period=_period(volume_mt=D("10")))


def test_volume_pct_requires_existing_volume() -> None:
    with pytest.raises(ScenarioError, match="volume"):
        _run(DeltaTarget.VOLUME, DeltaOp.PCT, "10", period=_period(volume_mt=None))


def test_volume_driven_negative_raises() -> None:
    with pytest.raises(ScenarioError, match="volume"):
        _run(DeltaTarget.VOLUME, DeltaOp.ABSOLUTE, "-50", period=_period(volume_mt=D("10")))


def test_opex_driven_negative_raises() -> None:
    from advisor.schema import OperatingExpenses

    with pytest.raises(ScenarioError, match="opex_administrative"):
        _run(
            DeltaTarget.OPEX_ADMINISTRATIVE,
            DeltaOp.SET,
            "-1",
            period=_period(opex=OperatingExpenses(administrative=D("50"))),
        )


def test_unknown_applies_to_period_raises() -> None:
    with pytest.raises(ScenarioError, match="not a period label"):
        _run(DeltaTarget.REVENUE, DeltaOp.PCT, "-10", applies_to="Q9 FY9999")
