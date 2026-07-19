"""Validator and serialization tests for the canonical schema."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from advisor.schema import (
    CONSISTENCY_TOL,
    EntityMeta,
    IncomeStatement,
    LineItem,
    OperatingExpenses,
    Period,
    PeriodMeta,
    PeriodType,
    SourceMeta,
    Status,
)


def _meta(seq: int = 0, label: str = "FY2023-24") -> PeriodMeta:
    return PeriodMeta(label=label, period_type=PeriodType.YEAR, fiscal_year=2024, sequence=seq)


def _period(seq: int = 0, label: str = "FY2023-24", **kwargs: object) -> Period:
    base: dict[str, object] = {
        "meta": _meta(seq, label),
        "revenue": Decimal("1000"),
        "cogs": Decimal("600"),
    }
    base.update(kwargs)
    return Period.model_validate(base)


# --- LineItem ------------------------------------------------------------- #
def test_lineitem_strips_whitespace_and_forbids_extra() -> None:
    item = LineItem(label="  Salary  ", amount=Decimal("10"))
    assert item.label == "Salary"
    with pytest.raises(ValidationError):
        LineItem(label="X", amount=Decimal("1"), foo=1)  # type: ignore[call-arg]


def test_lineitem_empty_label_rejected() -> None:
    with pytest.raises(ValidationError):
        LineItem(label="   ", amount=Decimal("1"))


def test_lineitem_allows_negative_amount() -> None:
    assert LineItem(label="Credit", amount=Decimal("-50")).amount == Decimal("-50")


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_decimal_nan_inf_rejected(bad: Decimal) -> None:
    with pytest.raises(ValidationError):
        LineItem(label="X", amount=bad)


# --- PeriodMeta ----------------------------------------------------------- #
@pytest.mark.parametrize("year,ok", [(1899, False), (2101, False), (2024, True)])
def test_periodmeta_fiscal_year_bounds(year: int, ok: bool) -> None:
    kwargs = {"label": "P", "period_type": PeriodType.YEAR, "fiscal_year": year, "sequence": 0}
    if ok:
        assert PeriodMeta(**kwargs).fiscal_year == year  # type: ignore[arg-type]
    else:
        with pytest.raises(ValidationError):
            PeriodMeta(**kwargs)  # type: ignore[arg-type]


def test_periodmeta_sequence_nonneg() -> None:
    with pytest.raises(ValidationError):
        PeriodMeta(label="P", period_type=PeriodType.YEAR, fiscal_year=2024, sequence=-1)
    assert _meta(0).sequence == 0


@pytest.mark.parametrize(
    "ptype,sub,ok",
    [
        (PeriodType.QUARTER, 5, False),
        (PeriodType.QUARTER, 4, True),
        (PeriodType.MONTH, 13, False),
        (PeriodType.HALF, 3, False),
        (PeriodType.HALF, 2, True),
    ],
)
def test_periodmeta_subindex_range_by_type(ptype: PeriodType, sub: int, ok: bool) -> None:
    kwargs = {
        "label": "P",
        "period_type": ptype,
        "fiscal_year": 2024,
        "sequence": 0,
        "sub_index": sub,
    }
    if ok:
        assert PeriodMeta(**kwargs).sub_index == sub  # type: ignore[arg-type]
    else:
        with pytest.raises(ValidationError):
            PeriodMeta(**kwargs)  # type: ignore[arg-type]


def test_periodmeta_date_order() -> None:
    with pytest.raises(ValidationError):
        PeriodMeta(
            label="P",
            period_type=PeriodType.YEAR,
            fiscal_year=2024,
            sequence=0,
            start_date=date(2024, 6, 30),
            end_date=date(2023, 7, 1),
        )
    PeriodMeta(
        label="P",
        period_type=PeriodType.YEAR,
        fiscal_year=2024,
        sequence=0,
        start_date=date(2023, 7, 1),
        end_date=date(2024, 6, 30),
    )


# --- OperatingExpenses ---------------------------------------------------- #
def test_operating_expenses_negative_category_rejected() -> None:
    with pytest.raises(ValidationError):
        OperatingExpenses(administrative=Decimal("-1"))


def test_operating_expenses_consistency_within_tolerance() -> None:
    oe = OperatingExpenses(
        selling_distribution=Decimal("100"),
        administrative=Decimal("200"),
        other_opex=Decimal("50"),
        total=Decimal("350") + CONSISTENCY_TOL,
    )
    assert oe.total is not None


def test_operating_expenses_consistency_violation_raises() -> None:
    with pytest.raises(ValidationError):
        OperatingExpenses(
            selling_distribution=Decimal("100"),
            administrative=Decimal("200"),
            other_opex=Decimal("50"),
            total=Decimal("1350"),
        )


# --- Period --------------------------------------------------------------- #
def test_period_requires_revenue_and_cogs() -> None:
    with pytest.raises(ValidationError):
        Period.model_validate({"meta": _meta(), "cogs": Decimal("1")})
    assert _period().revenue == Decimal("1000")


def test_period_negative_revenue_or_cogs_rejected() -> None:
    with pytest.raises(ValidationError):
        _period(revenue=Decimal("-1"))
    with pytest.raises(ValidationError):
        _period(cogs=Decimal("-1"))


def test_period_net_profit_may_be_negative() -> None:
    assert _period(net_profit=Decimal("-999")).net_profit == Decimal("-999")


def test_period_gross_profit_consistency() -> None:
    with pytest.raises(ValidationError):
        _period(gross_profit=Decimal("999"))  # revenue-cogs == 400
    assert _period(gross_profit=Decimal("400")).gross_profit == Decimal("400")
    assert _period(gross_profit=None).gross_profit is None


def test_period_volume_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        _period(volume_mt=Decimal("-1"))
    assert _period(volume_mt=None).volume_mt is None


# --- EntityMeta / SourceMeta --------------------------------------------- #
def test_entitymeta_defaults_are_neutral() -> None:
    e = EntityMeta()
    assert e.company_name == "Your Company"
    assert e.group_name == ""
    assert e.currency == "USD"
    assert e.volume_unit == "MT"
    assert e.fiscal_year_end_month == 12
    assert e.industry is None


def test_entitymeta_accepts_any_currency_and_unit() -> None:
    e = EntityMeta(company_name="A1 Polymer Ltd.", currency="BDT", volume_unit="kg")
    assert e.currency == "BDT"
    assert e.volume_unit == "kg"


def test_entitymeta_rejects_blank_currency_and_unit() -> None:
    with pytest.raises(ValidationError):
        EntityMeta(currency="")
    with pytest.raises(ValidationError):
        EntityMeta(volume_unit="")


@pytest.mark.parametrize("month,ok", [(0, False), (13, False), (6, True)])
def test_entitymeta_fy_end_month_bounds(month: int, ok: bool) -> None:
    if ok:
        assert EntityMeta(fiscal_year_end_month=month).fiscal_year_end_month == month
    else:
        with pytest.raises(ValidationError):
            EntityMeta(fiscal_year_end_month=month)


@pytest.mark.parametrize(
    "scale,ok", [(Decimal("0"), False), (Decimal("-1"), False), (Decimal("1000"), True)]
)
def test_sourcemeta_scale_positive(scale: Decimal, ok: bool) -> None:
    if ok:
        assert SourceMeta(source_scale=scale).source_scale == scale
    else:
        with pytest.raises(ValidationError):
            SourceMeta(source_scale=scale)


# --- IncomeStatement ------------------------------------------------------ #
def test_incomestatement_requires_at_least_one_period() -> None:
    with pytest.raises(ValidationError):
        IncomeStatement(periods=[])


def test_incomestatement_duplicate_sequence_rejected() -> None:
    with pytest.raises(ValidationError):
        IncomeStatement(periods=[_period(0, "A"), _period(0, "B")])


def test_incomestatement_duplicate_label_rejected() -> None:
    with pytest.raises(ValidationError):
        IncomeStatement(periods=[_period(0, "Same"), _period(1, "Same")])


def test_incomestatement_resorts_periods_by_sequence() -> None:
    stmt = IncomeStatement(periods=[_period(2, "C"), _period(0, "A"), _period(1, "B")])
    assert [p.meta.sequence for p in stmt.periods] == [0, 1, 2]
    assert [p.meta.label for p in stmt.periods] == ["A", "B", "C"]


# --- Enums / serialization ----------------------------------------------- #
def test_enums_serialize_to_lowercase_strings() -> None:
    assert Status.GREEN.value == "green"
    dumped = _period().model_dump(mode="json")
    assert dumped["meta"]["period_type"] == "year"
    assert dumped["meta"]["kind"] == "actual"


def test_models_json_roundtrip() -> None:
    stmt = IncomeStatement(periods=[_period(0, "A"), _period(1, "B")])
    rebuilt = IncomeStatement.model_validate(stmt.model_dump(mode="json"))
    assert rebuilt == stmt
