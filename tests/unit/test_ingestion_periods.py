"""Tests for period-header parsing and period-column detection."""

from __future__ import annotations

import pytest

from advisor.ingestion.errors import NoPeriodsFoundError, PeriodDetectionError
from advisor.ingestion.periods import detect_period_columns, parse_period_label
from advisor.schema import PeriodType


def test_parse_fy_label() -> None:
    meta = parse_period_label("FY2023-24", fiscal_year_end_month=6)
    assert meta.period_type is PeriodType.YEAR
    assert meta.fiscal_year == 2024
    assert meta.months == 12


def test_parse_fy_short_label() -> None:
    assert parse_period_label("FY24", fiscal_year_end_month=6).fiscal_year == 2024


def test_parse_quarter_label() -> None:
    meta = parse_period_label("Q1 FY2024", fiscal_year_end_month=6)
    assert meta.period_type is PeriodType.QUARTER
    assert meta.sub_index == 1
    assert meta.fiscal_year == 2024


def test_parse_month_label() -> None:
    meta = parse_period_label("Jan 2024", fiscal_year_end_month=6)
    assert meta.period_type is PeriodType.MONTH
    assert meta.fiscal_year == 2024  # Jan falls in a July-June FY ending 2024
    assert meta.sub_index == 7  # 7th month of a July-start fiscal year
    assert meta.months == 1


def test_parse_half_label() -> None:
    meta = parse_period_label("H1 FY2024", fiscal_year_end_month=6)
    assert meta.period_type is PeriodType.HALF
    assert meta.sub_index == 1
    assert meta.months == 6


def test_parse_full_fy_label() -> None:
    assert parse_period_label("FY2024", fiscal_year_end_month=6).fiscal_year == 2024


def test_parse_plain_year_range() -> None:
    meta = parse_period_label("2022-2023", fiscal_year_end_month=6)
    assert meta.period_type is PeriodType.YEAR
    assert meta.fiscal_year == 2023


def test_parse_plain_year() -> None:
    assert parse_period_label("2024", fiscal_year_end_month=6).fiscal_year == 2024


def test_parse_quarter_without_year_raises() -> None:
    with pytest.raises(PeriodDetectionError):
        parse_period_label("Q1", fiscal_year_end_month=6)


def test_parse_unparseable_raises() -> None:
    with pytest.raises(PeriodDetectionError):
        parse_period_label("Random Header", fiscal_year_end_month=6)


def test_detect_columns_orders_and_sequences() -> None:
    # Provided newest-first; expect oldest-first with sequence 0..n-1.
    cols = detect_period_columns([(1, "FY2023-24"), (2, "FY2022-23")], fiscal_year_end_month=6)
    assert [c.meta.sequence for c in cols] == [0, 1]
    assert [c.meta.fiscal_year for c in cols] == [2023, 2024]
    assert [c.col_index for c in cols] == [2, 1]


def test_detect_skips_non_period_columns() -> None:
    cols = detect_period_columns(
        [(1, "Notes"), (2, "FY2022-23"), (3, "FY2023-24")], fiscal_year_end_month=6
    )
    assert len(cols) == 2


def test_detect_no_periods_raises() -> None:
    with pytest.raises(NoPeriodsFoundError):
        detect_period_columns([(1, "Particulars"), (2, "Notes")], fiscal_year_end_month=6)
