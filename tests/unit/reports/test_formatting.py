"""Tests for the deterministic report formatters."""

from __future__ import annotations

from decimal import Decimal

import pytest

from advisor.reports.formatting import (
    NA,
    excel_number_format,
    format_bps,
    format_money,
    format_pct,
    format_per_unit,
    format_volume,
    status_hex,
)
from advisor.schema import Status


def test_format_money_western_grouping_default() -> None:
    assert format_money(Decimal("12345678")) == "USD 12,345,678"
    assert format_money(Decimal("999")) == "USD 999"


def test_format_money_currency_configurable() -> None:
    assert format_money(Decimal("1000"), currency="EUR") == "EUR 1,000"


def test_format_money_south_asian_grouping() -> None:
    assert (
        format_money(Decimal("12345678"), currency="BDT", grouping="south_asian")
        == "BDT 1,23,45,678"
    )
    assert format_money(Decimal("999"), currency="BDT", grouping="south_asian") == "BDT 999"


def test_format_money_negative_parenthesised() -> None:
    assert format_money(Decimal("-1000")) == "(USD 1,000)"


def test_format_money_none() -> None:
    assert format_money(None) == NA


def test_formatters_reject_float() -> None:
    with pytest.raises(TypeError):
        format_money(1.5)  # type: ignore[arg-type]


def test_format_pct_volume_and_per_unit() -> None:
    assert format_pct(Decimal("18.4567")) == "18.46%"
    assert format_volume(Decimal("1234.5")) == "1,234.50 MT"
    assert format_volume(Decimal("12.5"), unit="kg") == "12.50 kg"
    assert format_per_unit(Decimal("1234.5"), currency="BDT", unit="MT") == "BDT 1,234.50 /MT"
    assert format_per_unit(Decimal("2.5")) == "USD 2.50 /MT"


def test_format_bps_signed() -> None:
    assert format_bps(Decimal("200")) == "+200 bps"
    assert format_bps(Decimal("-150")) == "-150 bps"
    assert format_bps(None) == NA


def test_status_hex_and_excel_format() -> None:
    assert status_hex(Status.GREEN) == "2E7D32"
    assert "USD" in excel_number_format("money")
    assert excel_number_format("pct").endswith('"%"')
    fmt = excel_number_format("per_unit", currency="EUR", unit="kg")
    assert "EUR" in fmt and "kg" in fmt
