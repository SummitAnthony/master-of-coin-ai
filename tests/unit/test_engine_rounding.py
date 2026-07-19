"""Tests for the deterministic Decimal helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from advisor.engine.rounding import (
    MONEY_QUANT,
    PCT_QUANT,
    direction_of,
    pct_of,
    per_mt,
    quantize_money,
    quantize_pct,
    quantize_per_mt,
    safe_div,
)
from advisor.schema import Direction


def test_quantizers_round_half_up() -> None:
    assert quantize_money(Decimal("1.005")) == Decimal("1.01")
    assert quantize_pct(Decimal("1.00005")) == Decimal("1.0001")
    assert quantize_per_mt(Decimal("2.005")) == Decimal("2.01")


@pytest.mark.parametrize("denom", [None, Decimal("0"), Decimal("-5")])
def test_safe_div_guards(denom: Decimal | None) -> None:
    assert safe_div(Decimal("10"), denom, MONEY_QUANT) is None


def test_safe_div_value() -> None:
    assert safe_div(Decimal("10"), Decimal("4"), MONEY_QUANT) == Decimal("2.50")


@pytest.mark.parametrize("whole", [None, Decimal("0"), Decimal("-1")])
def test_pct_of_guards(whole: Decimal | None) -> None:
    assert pct_of(Decimal("50"), whole) is None


def test_pct_of_value() -> None:
    assert pct_of(Decimal("50"), Decimal("200")) == Decimal("25.0000")


def test_per_mt_value_and_guard() -> None:
    assert per_mt(Decimal("1000"), Decimal("10")) == Decimal("100.00")
    assert per_mt(Decimal("1000"), None) is None


def test_direction_of() -> None:
    assert direction_of(None) is Direction.FLAT
    assert direction_of(Decimal("0.00005")) is Direction.FLAT  # within epsilon
    assert direction_of(PCT_QUANT) is Direction.FLAT  # exactly epsilon -> flat
    assert direction_of(Decimal("1")) is Direction.UP
    assert direction_of(Decimal("-1")) is Direction.DOWN
