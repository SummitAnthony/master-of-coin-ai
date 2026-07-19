"""Tests for reporting-scale detection."""

from __future__ import annotations

from decimal import Decimal

from advisor.ingestion.scale import detect_scale


def test_detect_default_one() -> None:
    assert detect_scale(["Particulars", "FY2023-24"]) == Decimal("1")


def test_detect_thousands() -> None:
    assert detect_scale(["Amounts in 000"]) == Decimal("1000")
    assert detect_scale(["in '000 BDT"]) == Decimal("1000")


def test_detect_lakh_and_crore() -> None:
    assert detect_scale(["figures in lakh"]) == Decimal("100000")
    assert detect_scale(["in crore"]) == Decimal("10000000")


def test_detect_million() -> None:
    assert detect_scale(["figures in million"]) == Decimal("1000000")


def test_override_takes_precedence() -> None:
    assert detect_scale(["in crore"], override=Decimal("1")) == Decimal("1")


def test_longest_keyword_wins() -> None:
    # crore precedes lakh in the ordered table -> deterministic.
    assert detect_scale(["in lakh and crore"]) == Decimal("10000000")
