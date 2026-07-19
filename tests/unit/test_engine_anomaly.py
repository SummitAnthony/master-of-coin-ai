"""Tests for the config-driven anomaly rules."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from advisor.engine.anomaly import (
    check_cogs_outpacing_sales,
    check_cost_spikes,
    check_margin_drop,
    detect_anomalies,
)
from advisor.schema import PeriodKPIs, PeriodRef, PeriodType

D = Decimal
_ANOMS = {"margin_drop_bps": 200, "cogs_vs_sales_growth_gap_pct": 3.0, "cost_spike_pct": 15.0}


def _k(
    seq: int,
    rev: Decimal,
    cogs: Decimal,
    *,
    total_opex: Decimal = D("100"),
    finance: Decimal = D("0"),
    gm: Decimal | None = None,
    om: Decimal | None = None,
    nm: Decimal | None = None,
) -> PeriodKPIs:
    return PeriodKPIs(
        period=PeriodRef(
            label=f"P{seq}", period_type=PeriodType.YEAR, fiscal_year=2024, sequence=seq
        ),
        revenue=rev,
        cogs=cogs,
        gross_profit=rev - cogs,
        total_opex=total_opex,
        operating_profit=D("0"),
        other_income=D("0"),
        finance_cost=finance,
        profit_before_tax=D("0"),
        tax_expense=D("0"),
        net_profit=D("0"),
        gross_margin_pct=gm,
        operating_margin_pct=om,
        net_margin_pct=nm,
    )


def test_cogs_outpacing_fires() -> None:
    a = check_cogs_outpacing_sales(_k(0, D("1000"), D("600")), _k(1, D("1100"), D("720")), D("3"))
    assert a is not None
    assert a.code == "cogs_outpacing_sales"
    assert a.message_code == "cogs_outpacing_sales.warning"
    assert a.context["gap_pct"] == a.observed


def test_cogs_outpacing_no_fire_within_gap() -> None:
    assert (
        check_cogs_outpacing_sales(_k(0, D("1000"), D("600")), _k(1, D("1100"), D("630")), D("3"))
        is None
    )


def test_cogs_outpacing_none_when_base_zero() -> None:
    assert (
        check_cogs_outpacing_sales(_k(0, D("0"), D("600")), _k(1, D("1100"), D("720")), D("3"))
        is None
    )


def test_margin_drop_fires_and_skips_none() -> None:
    out = check_margin_drop(
        _k(0, D("1000"), D("600"), gm=D("40")), _k(1, D("1000"), D("600"), gm=D("35")), D("200")
    )
    assert [a.metric for a in out] == ["gross_margin_pct"]  # op/net are None -> skipped
    assert out[0].observed == D("500.00")


def test_margin_drop_no_fire_small() -> None:
    out = check_margin_drop(
        _k(0, D("1000"), D("600"), gm=D("40")), _k(1, D("1000"), D("600"), gm=D("39")), D("200")
    )
    assert out == []


def test_cost_spike_fires_and_skips_none() -> None:
    out = check_cost_spikes(
        _k(0, D("1000"), D("600"), finance=D("0")),
        _k(1, D("1000"), D("720"), finance=D("0")),
        D("15"),
    )
    # cogs +20% fires; total_opex flat; finance base 0 -> skipped
    assert [a.metric for a in out] == ["cogs"]


def test_cost_spike_no_fire() -> None:
    out = check_cost_spikes(_k(0, D("1000"), D("600")), _k(1, D("1000"), D("630")), D("15"))
    assert out == []


def test_detect_anomalies_collects_and_sorts() -> None:
    prev = _k(
        0,
        D("1000"),
        D("600"),
        total_opex=D("100"),
        finance=D("10"),
        gm=D("40"),
        om=D("30"),
        nm=D("20"),
    )
    curr = _k(
        1,
        D("1100"),
        D("800"),
        total_opex=D("160"),
        finance=D("20"),
        gm=D("30"),
        om=D("20"),
        nm=D("10"),
    )
    out = detect_anomalies([prev, curr], {"anomalies": _ANOMS})
    counts = Counter(a.code for a in out)
    assert counts == {"cogs_outpacing_sales": 1, "margin_drop": 3, "cost_spike": 3}
    assert out[0].code == "cogs_outpacing_sales"  # sorts before cost_spike/margin_drop
    assert all(a.period == "P1" for a in out)


def test_detect_anomalies_empty_config() -> None:
    kpis = [_k(0, D("1000"), D("600")), _k(1, D("1100"), D("800"))]
    assert detect_anomalies(kpis, {"anomalies": {}}) == []
    assert detect_anomalies(kpis, {}) == []
