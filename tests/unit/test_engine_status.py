"""Tests for threshold parsing and traffic-light classification."""

from __future__ import annotations

from decimal import Decimal

import pytest

from advisor.engine.status import (
    ThresholdRule,
    classify,
    evaluate_all_statuses,
    evaluate_status,
    parse_threshold_rules,
)
from advisor.schema import PeriodKPIs, PeriodRef, PeriodType, Status, ThresholdDirection

THRESHOLDS = {
    "margins": {
        "gross_margin_pct": {"green": 18.0, "yellow": 12.0, "direction": "higher_is_better"},
        "net_margin_pct": {"green": 6.0, "yellow": 2.0, "direction": "higher_is_better"},
    },
    "ratios": {
        "finance_cost_to_sales_pct": {"green": 3.0, "yellow": 6.0, "direction": "lower_is_better"},
    },
}

_HIGHER = ThresholdRule("m", Decimal("18"), Decimal("12"), ThresholdDirection.HIGHER_IS_BETTER)
_LOWER = ThresholdRule("r", Decimal("3"), Decimal("6"), ThresholdDirection.LOWER_IS_BETTER)


def test_parse_threshold_rules() -> None:
    rules = parse_threshold_rules(THRESHOLDS)
    assert set(rules) == {"gross_margin_pct", "net_margin_pct", "finance_cost_to_sales_pct"}
    assert rules["gross_margin_pct"].green_at == Decimal("18.0")
    assert rules["finance_cost_to_sales_pct"].direction is ThresholdDirection.LOWER_IS_BETTER


@pytest.mark.parametrize(
    "value,expected",
    [
        (Decimal("20"), Status.GREEN),
        (Decimal("18"), Status.GREEN),
        (Decimal("15"), Status.YELLOW),
        (Decimal("12"), Status.YELLOW),
        (Decimal("5"), Status.RED),
        (None, Status.UNKNOWN),
    ],
)
def test_classify_higher_is_better(value: Decimal | None, expected: Status) -> None:
    assert classify(value, _HIGHER) is expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (Decimal("2"), Status.GREEN),
        (Decimal("3"), Status.GREEN),
        (Decimal("5"), Status.YELLOW),
        (Decimal("6"), Status.YELLOW),
        (Decimal("8"), Status.RED),
    ],
)
def test_classify_lower_is_better(value: Decimal, expected: Status) -> None:
    assert classify(value, _LOWER) is expected


def test_evaluate_status_message_code() -> None:
    status = evaluate_status("gross_margin_pct", "FY2024", Decimal("20"), _HIGHER)
    assert status.status is Status.GREEN
    assert status.message_code == "gross_margin_pct.green"
    assert status.green_at == Decimal("18")


def _kpis(seq: int, gross: Decimal, net: Decimal, fin: Decimal) -> PeriodKPIs:
    return PeriodKPIs(
        period=PeriodRef(
            label=f"P{seq}", period_type=PeriodType.YEAR, fiscal_year=2024, sequence=seq
        ),
        revenue=Decimal("1000"),
        cogs=Decimal("600"),
        gross_profit=Decimal("400"),
        total_opex=Decimal("100"),
        operating_profit=Decimal("300"),
        other_income=Decimal("0"),
        finance_cost=Decimal("0"),
        profit_before_tax=Decimal("300"),
        tax_expense=Decimal("0"),
        net_profit=Decimal("300"),
        gross_margin_pct=gross,
        net_margin_pct=net,
        finance_cost_to_sales_pct=fin,
    )


def test_evaluate_all_statuses_order_and_count() -> None:
    kpis = [
        _kpis(0, Decimal("20"), Decimal("5"), Decimal("2")),
        _kpis(1, Decimal("10"), Decimal("1"), Decimal("8")),
    ]
    statuses = evaluate_all_statuses(kpis, THRESHOLDS)
    assert len(statuses) == 6  # 2 periods x 3 rules
    # First period, metrics sorted alphabetically.
    first = [(s.period, s.metric) for s in statuses[:3]]
    assert first == [
        ("P0", "finance_cost_to_sales_pct"),
        ("P0", "gross_margin_pct"),
        ("P0", "net_margin_pct"),
    ]
