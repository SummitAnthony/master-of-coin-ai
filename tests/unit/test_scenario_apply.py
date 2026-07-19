"""Tests for apply_scenario: per-target transforms, composition, immutability."""

from __future__ import annotations

from decimal import Decimal

from advisor.engine.scenario import apply_scenario
from advisor.schema import (
    AssumptionDelta,
    DeltaOp,
    DeltaTarget,
    IncomeStatement,
    LineItem,
    OperatingExpenses,
    Period,
    PeriodMeta,
    PeriodType,
    Scenario,
)

D = Decimal


def _period(label: str = "FY2023-24", seq: int = 0, fy: int = 2024, **over: object) -> Period:
    data: dict[str, object] = {
        "meta": PeriodMeta(label=label, period_type=PeriodType.YEAR, fiscal_year=fy, sequence=seq),
        "revenue": D("1000"),
        "cogs": D("600"),
    }
    data.update(over)
    return Period.model_validate(data)


def _stmt(*periods: Period) -> IncomeStatement:
    return IncomeStatement(periods=list(periods) if periods else [_period()])


def _delta(target: DeltaTarget, op: DeltaOp, mag: str, applies_to: str | None = None) -> Scenario:
    return Scenario(
        name="s",
        deltas=[AssumptionDelta(target=target, op=op, magnitude=D(mag), applies_to=applies_to)],
    )


def test_revenue_pct_decrease() -> None:
    out = apply_scenario(_stmt(), _delta(DeltaTarget.REVENUE, DeltaOp.PCT, "-10"))
    assert out.periods[0].revenue == D("900")
    assert out.periods[0].gross_profit is None  # cleared


def test_revenue_absolute_and_set() -> None:
    added = apply_scenario(_stmt(), _delta(DeltaTarget.REVENUE, DeltaOp.ABSOLUTE, "250"))
    assert added.periods[0].revenue == D("1250")
    setv = apply_scenario(_stmt(), _delta(DeltaTarget.REVENUE, DeltaOp.SET, "777"))
    assert setv.periods[0].revenue == D("777")


def test_cogs_pct_increase() -> None:
    out = apply_scenario(_stmt(), _delta(DeltaTarget.COGS, DeltaOp.PCT, "8"))
    assert out.periods[0].cogs == D("648")
    assert out.periods[0].gross_profit is None


def test_price_per_mt_pct_equals_revenue_pct() -> None:
    out = apply_scenario(
        _stmt(_period(volume_mt=D("10"))), _delta(DeltaTarget.PRICE_PER_MT, DeltaOp.PCT, "5")
    )
    assert out.periods[0].revenue == D("1050")
    assert out.periods[0].volume_mt == D("10")


def test_price_per_mt_absolute_uses_volume() -> None:
    out = apply_scenario(
        _stmt(_period(volume_mt=D("10"))), _delta(DeltaTarget.PRICE_PER_MT, DeltaOp.ABSOLUTE, "5")
    )
    assert out.periods[0].revenue == D("1050")  # 1000 + 5*10


def test_price_per_mt_set_uses_volume() -> None:
    out = apply_scenario(
        _stmt(_period(volume_mt=D("10"))), _delta(DeltaTarget.PRICE_PER_MT, DeltaOp.SET, "120")
    )
    assert out.periods[0].revenue == D("1200")  # 120*10


def test_volume_pct_changes_volume_only() -> None:
    out = apply_scenario(
        _stmt(_period(volume_mt=D("100"))), _delta(DeltaTarget.VOLUME, DeltaOp.PCT, "10")
    )
    assert out.periods[0].volume_mt == D("110")
    assert out.periods[0].revenue == D("1000")
    assert out.periods[0].cogs == D("600")


def test_volume_set_when_none() -> None:
    out = apply_scenario(
        _stmt(_period(volume_mt=None)), _delta(DeltaTarget.VOLUME, DeltaOp.SET, "50")
    )
    assert out.periods[0].volume_mt == D("50")


def test_volume_absolute() -> None:
    out = apply_scenario(
        _stmt(_period(volume_mt=D("100"))), _delta(DeltaTarget.VOLUME, DeltaOp.ABSOLUTE, "-20")
    )
    assert out.periods[0].volume_mt == D("80")


def test_finance_other_income_tax_deltas() -> None:
    base = _period(finance_cost=D("40"), other_income=D("10"), tax_expense=D("20"))
    fin = apply_scenario(_stmt(base), _delta(DeltaTarget.FINANCE_COST, DeltaOp.PCT, "25"))
    assert fin.periods[0].finance_cost == D("50")
    oth = apply_scenario(_stmt(base), _delta(DeltaTarget.OTHER_INCOME, DeltaOp.ABSOLUTE, "5"))
    assert oth.periods[0].other_income == D("15")
    tax = apply_scenario(_stmt(base), _delta(DeltaTarget.TAX_EXPENSE, DeltaOp.SET, "0"))
    assert tax.periods[0].tax_expense == D("0")


def test_finance_cost_from_none_base_zero() -> None:
    out = apply_scenario(_stmt(_period()), _delta(DeltaTarget.FINANCE_COST, DeltaOp.ABSOLUTE, "30"))
    assert out.periods[0].finance_cost == D("30")  # None treated as 0


def test_opex_category_pct_clears_total() -> None:
    base = _period(
        opex=OperatingExpenses(
            administrative=D("50"),
            selling_distribution=D("30"),
            other_opex=D("20"),
            total=D("100"),
        )
    )
    out = apply_scenario(_stmt(base), _delta(DeltaTarget.OPEX_ADMINISTRATIVE, DeltaOp.PCT, "10"))
    assert out.periods[0].opex.administrative == D("55")
    assert out.periods[0].opex.total is None


def test_opex_selling_and_other_targets() -> None:
    base = _period(opex=OperatingExpenses(selling_distribution=D("30"), other_opex=D("20")))
    s = apply_scenario(
        _stmt(base), _delta(DeltaTarget.OPEX_SELLING_DISTRIBUTION, DeltaOp.ABSOLUTE, "10")
    )
    assert s.periods[0].opex.selling_distribution == D("40")
    o = apply_scenario(_stmt(base), _delta(DeltaTarget.OPEX_OTHER, DeltaOp.SET, "5"))
    assert o.periods[0].opex.other_opex == D("5")


def test_multiple_deltas_compose_in_order() -> None:
    scenario = Scenario(
        name="s",
        deltas=[
            AssumptionDelta(target=DeltaTarget.REVENUE, op=DeltaOp.PCT, magnitude=D("-10")),
            AssumptionDelta(target=DeltaTarget.REVENUE, op=DeltaOp.PCT, magnitude=D("5")),
        ],
    )
    out = apply_scenario(_stmt(), scenario)
    assert out.periods[0].revenue == D("1000") * D("0.9") * D("1.05")


def test_applies_to_single_period_only() -> None:
    stmt = _stmt(_period("FY2022-23", 0, 2023), _period("FY2023-24", 1, 2024))
    out = apply_scenario(
        stmt, _delta(DeltaTarget.REVENUE, DeltaOp.PCT, "-10", applies_to="FY2023-24")
    )
    assert out.periods[0].revenue == D("1000")  # untouched
    assert out.periods[1].revenue == D("900")


def test_empty_deltas_returns_equal_statement() -> None:
    stmt = _stmt(_period(gross_profit=D("400")))
    out = apply_scenario(stmt, Scenario(name="noop"))
    assert out.model_dump() == stmt.model_dump()


def test_base_statement_not_mutated() -> None:
    stmt = _stmt()
    snapshot = stmt.model_dump()
    out = apply_scenario(stmt, _delta(DeltaTarget.REVENUE, DeltaOp.PCT, "-10"))
    assert stmt.model_dump() == snapshot
    assert out is not stmt
    assert out.periods[0] is not stmt.periods[0]


def test_provenance_preserved() -> None:
    base = _period(
        extra_lines=[LineItem(label="Note", amount=D("5"), source_ref="C9")],
        opex=OperatingExpenses(
            items=[LineItem(label="Rent", amount=D("10"), category="other_opex")]
        ),
    )
    out = apply_scenario(_stmt(base), _delta(DeltaTarget.REVENUE, DeltaOp.PCT, "-10"))
    assert out.periods[0].extra_lines[0].label == "Note"
    assert out.periods[0].opex.items[0].label == "Rent"


def test_full_precision_no_quantization() -> None:
    out = apply_scenario(_stmt(), _delta(DeltaTarget.REVENUE, DeltaOp.PCT, "-3.333"))
    # 1000 * (1 - 0.03333) = 966.70 exactly, full precision retained (no 0.01 rounding artifact)
    assert out.periods[0].revenue == D("1000") * (D("1") + D("-3.333") / D("100"))
