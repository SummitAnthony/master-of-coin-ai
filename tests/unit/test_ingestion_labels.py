"""Tests for label normalization and canonical line matching."""

from __future__ import annotations

import pytest

from advisor.ingestion.errors import AmbiguousLabelError
from advisor.ingestion.labels import LineKey, match_line, normalize_label


def test_normalize_label_casefolds_and_collapses() -> None:
    assert normalize_label("  Cost  of   Sales: ") == "cost of sales"


@pytest.mark.parametrize("raw", ["Turnover", "Net Sales", "SALES"])
def test_match_canonical_synonyms_revenue(raw: str) -> None:
    assert match_line(raw) is LineKey.REVENUE


@pytest.mark.parametrize("raw", ["Cost of Goods Sold", "Cost of Sales"])
def test_match_cogs_variants(raw: str) -> None:
    assert match_line(raw) is LineKey.COGS


@pytest.mark.parametrize("raw", ["Financial Expenses", "Interest Expense"])
def test_match_finance_cost_variants(raw: str) -> None:
    assert match_line(raw) is LineKey.FINANCE_COST


def test_match_opex_categories() -> None:
    assert match_line("Administrative Expenses") is LineKey.OPEX_ADMINISTRATIVE
    assert match_line("Selling & Distribution") is LineKey.OPEX_SELLING_DISTRIBUTION


def test_match_profit_lines() -> None:
    assert match_line("Profit Before Tax") is LineKey.PROFIT_BEFORE_TAX
    assert match_line("Profit After Tax") is LineKey.NET_PROFIT
    assert match_line("Net Profit") is LineKey.NET_PROFIT
    assert match_line("Gross Profit") is LineKey.GROSS_PROFIT


def test_match_volume() -> None:
    assert match_line("Sales Volume (MT)") is LineKey.VOLUME_MT


def test_match_unknown_returns_none() -> None:
    assert match_line("Miscellaneous note") is None


def test_match_ambiguous_raises_when_coord_given() -> None:
    with pytest.raises(AmbiguousLabelError) as ei:
        match_line("Other Income Tax", coord="A5")
    assert ei.value.coord == "A5"
    assert "other_income" in ei.value.candidates
    assert "tax_expense" in ei.value.candidates


def test_match_ambiguous_without_coord_returns_none() -> None:
    assert match_line("Other Income Tax") is None
