"""Tests for variance pairing and per-metric change computation."""

from __future__ import annotations

from decimal import Decimal

from advisor.engine.variance import (
    compute_all_variances,
    compute_variance,
    period_pairs,
)
from advisor.schema import (
    Direction,
    PeriodKPIs,
    PeriodMeta,
    PeriodRef,
    PeriodType,
    VarianceBasis,
)

D = Decimal


def _meta(
    seq: int, fy: int = 2024, pt: PeriodType = PeriodType.YEAR, sub: int | None = None
) -> PeriodMeta:
    return PeriodMeta(label=f"P{seq}", period_type=pt, fiscal_year=fy, sequence=seq, sub_index=sub)


def _kpis(seq: int, pt: PeriodType = PeriodType.YEAR, fy: int = 2024, **over: object) -> PeriodKPIs:
    data: dict[str, object] = {
        "period": PeriodRef(label=f"P{seq}", period_type=pt, fiscal_year=fy, sequence=seq),
        "revenue": D("1000"),
        "cogs": D("600"),
        "gross_profit": D("400"),
        "total_opex": D("100"),
        "operating_profit": D("300"),
        "other_income": D("0"),
        "finance_cost": D("0"),
        "profit_before_tax": D("300"),
        "tax_expense": D("0"),
        "net_profit": D("300"),
    }
    data.update(over)
    return PeriodKPIs.model_validate(data)


def test_pairs_sequential() -> None:
    metas = [_meta(0), _meta(1), _meta(2)]
    assert period_pairs(metas, VarianceBasis.SEQUENTIAL) == [(0, 1), (1, 2)]


def test_pairs_mom_only_consecutive_months() -> None:
    metas = [
        _meta(0, pt=PeriodType.YEAR),
        _meta(1, pt=PeriodType.MONTH),
        _meta(2, pt=PeriodType.MONTH),
    ]
    assert period_pairs(metas, VarianceBasis.MOM) == [(1, 2)]


def test_pairs_qoq_only_quarters() -> None:
    metas = [_meta(0, pt=PeriodType.QUARTER), _meta(1, pt=PeriodType.QUARTER)]
    assert period_pairs(metas, VarianceBasis.QOQ) == [(0, 1)]


def test_pairs_yoy_year() -> None:
    metas = [_meta(0, fy=2022), _meta(1, fy=2023), _meta(2, fy=2024)]
    assert period_pairs(metas, VarianceBasis.YOY) == [(0, 1), (1, 2)]


def test_pairs_yoy_quarter_matches_sub_index() -> None:
    metas = [
        _meta(0, fy=2023, pt=PeriodType.QUARTER, sub=1),
        _meta(1, fy=2024, pt=PeriodType.QUARTER, sub=1),
        _meta(2, fy=2024, pt=PeriodType.QUARTER, sub=2),
    ]
    assert period_pairs(metas, VarianceBasis.YOY) == [(0, 1)]


def test_pairs_yoy_none_when_single_year() -> None:
    assert period_pairs([_meta(0)], VarianceBasis.YOY) == []


def test_pairs_yoy_mixed_types_none() -> None:
    metas = [
        _meta(0, fy=2023, pt=PeriodType.YEAR),
        _meta(1, fy=2024, pt=PeriodType.QUARTER, sub=1),
    ]
    assert period_pairs(metas, VarianceBasis.YOY) == []


def test_variance_money_metric() -> None:
    v = compute_variance(
        "revenue",
        VarianceBasis.SEQUENTIAL,
        _kpis(0, revenue=D("900")),
        _kpis(1, revenue=D("1000")),
    )
    assert v.absolute_change == D("100.00")
    assert v.pct_change == D("11.1111")
    assert v.bps_change is None
    assert v.direction is Direction.UP


def test_variance_pct_metric_sets_bps() -> None:
    v = compute_variance(
        "gross_margin_pct",
        VarianceBasis.SEQUENTIAL,
        _kpis(0, gross_margin_pct=D("20")),
        _kpis(1, gross_margin_pct=D("25")),
    )
    assert v.absolute_change == D("5.0000")
    assert v.bps_change == D("500.00")
    assert v.pct_change == D("25.0000")
    assert v.direction is Direction.UP


def test_variance_from_none_is_flat() -> None:
    v = compute_variance(
        "volume_mt", VarianceBasis.SEQUENTIAL, _kpis(0, volume_mt=None), _kpis(1, volume_mt=D("10"))
    )
    assert v.absolute_change is None
    assert v.pct_change is None
    assert v.direction is Direction.FLAT


def test_variance_from_zero_has_no_pct() -> None:
    v = compute_variance(
        "volume_mt",
        VarianceBasis.SEQUENTIAL,
        _kpis(0, volume_mt=D("0")),
        _kpis(1, volume_mt=D("100")),
    )
    assert v.absolute_change == D("100.00")
    assert v.pct_change is None  # base <= 0
    assert v.direction is Direction.UP


def test_variance_to_none() -> None:
    v = compute_variance(
        "volume_mt", VarianceBasis.SEQUENTIAL, _kpis(0, volume_mt=D("10")), _kpis(1, volume_mt=None)
    )
    assert v.absolute_change is None
    assert v.bps_change is None


def test_variance_down_direction() -> None:
    v = compute_variance(
        "revenue",
        VarianceBasis.SEQUENTIAL,
        _kpis(0, revenue=D("100")),
        _kpis(1, revenue=D("90")),
    )
    assert v.direction is Direction.DOWN


def test_compute_all_variances_order_and_skip() -> None:
    metas = [_meta(0), _meta(1)]
    kpis = [
        _kpis(0, revenue=D("900"), gross_margin_pct=D("20")),
        _kpis(1, revenue=D("1000"), gross_margin_pct=D("25")),
    ]
    out = compute_all_variances(
        kpis, metas, metrics=("revenue", "gross_margin_pct"), bases=(VarianceBasis.SEQUENTIAL,)
    )
    assert [v.metric for v in out] == ["revenue", "gross_margin_pct"]


def test_compute_all_variances_skips_all_none() -> None:
    metas = [_meta(0), _meta(1)]
    kpis = [_kpis(0, volume_mt=None), _kpis(1, volume_mt=None)]
    out = compute_all_variances(
        kpis, metas, metrics=("volume_mt",), bases=(VarianceBasis.SEQUENTIAL,)
    )
    assert out == []
