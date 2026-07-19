"""Tests for the pure amount parser."""

from __future__ import annotations

from decimal import Decimal

import pytest

from advisor.ingestion.errors import CellParseError
from advisor.ingestion.numbers import is_blank, parse_amount


def test_parse_plain_int_and_float() -> None:
    assert parse_amount(1234) == Decimal("1234")
    assert parse_amount(12.5) == Decimal("12.5")  # no binary float artifacts


def test_parse_comma_grouping() -> None:
    assert parse_amount("1,234,567") == Decimal("1234567")


def test_parse_parentheses_negative() -> None:
    assert parse_amount("(1,234.56)") == Decimal("-1234.56")


@pytest.mark.parametrize(
    "raw", ["৳ 1,000", "Tk 1000", "BDT 1000", "$ 1,000", "€1000", "£1,000", "₹1000", "USD 1000"]
)
def test_parse_currency_symbols(raw: str) -> None:
    assert parse_amount(raw) == Decimal("1000")


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_blank_returns_none(raw: object) -> None:
    assert parse_amount(raw) is None


@pytest.mark.parametrize("raw", ["-", "–", "n/a", "NA"])  # noqa: RUF001
def test_parse_dash_placeholder_returns_none(raw: str) -> None:
    assert parse_amount(raw) is None


def test_parse_passes_through_decimal() -> None:
    value = Decimal("5.00")
    assert parse_amount(value) == value


def test_parse_junk_raises_cellparseerror() -> None:
    with pytest.raises(CellParseError) as ei:
        parse_amount("see note 4", coord="C9")
    assert ei.value.coord == "C9"
    assert ei.value.raw == "see note 4"


def test_parse_bool_raises() -> None:
    with pytest.raises(CellParseError):
        parse_amount(True, coord="A1")


def test_is_blank_matches_placeholders() -> None:
    assert is_blank(None)
    assert is_blank("  ")
    assert is_blank("-")
    assert not is_blank("0")
    assert not is_blank("5")
