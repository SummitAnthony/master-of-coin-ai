"""Tests for the pure extraction core (extract_from_grid)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from advisor.ingestion.errors import MissingRequiredLineError
from advisor.ingestion.extractor import ExtractOptions, extract_from_grid
from advisor.ingestion.workbook import grid_from_rows
from advisor.schema import EntityMeta, SourceMeta


def test_extract_clean_single_period() -> None:
    grid = grid_from_rows(
        "PnL", [["Particulars", "FY2023-24"], ["Revenue", 1000], ["Cost of Sales", 600]]
    )
    stmt = extract_from_grid(grid, options=ExtractOptions())
    assert len(stmt.periods) == 1
    p = stmt.periods[0]
    assert p.revenue == Decimal("1000")
    assert p.cogs == Decimal("600")
    # As-reported: optional subtotals are NOT derived by ingestion.
    assert p.gross_profit is None
    assert p.operating_profit is None
    assert p.net_profit is None


def test_extract_multi_period() -> None:
    grid = grid_from_rows(
        "PnL",
        [
            ["Particulars", "FY2022-23", "FY2023-24"],
            ["Revenue", 900, 1000],
            ["COGS", 500, 600],
        ],
    )
    stmt = extract_from_grid(grid, options=ExtractOptions())
    assert [p.meta.sequence for p in stmt.periods] == [0, 1]
    assert [p.meta.fiscal_year for p in stmt.periods] == [2023, 2024]
    assert stmt.periods[0].revenue == Decimal("900")
    assert stmt.periods[1].revenue == Decimal("1000")


def test_extract_threads_entity_metadata() -> None:
    grid = grid_from_rows(
        "PnL", [["Particulars", "Jul 2023"], ["Revenue", 1000], ["Cost of Sales", 600]]
    )
    entity = EntityMeta(company_name="A1 Polymer Ltd.", currency="BDT", fiscal_year_end_month=6)
    stmt = extract_from_grid(grid, options=ExtractOptions(entity=entity))
    assert stmt.entity == entity
    # July opens a June-ending fiscal year: Jul 2023 belongs to FY2024, sub-index 1.
    assert stmt.periods[0].meta.fiscal_year == 2024
    assert stmt.periods[0].meta.sub_index == 1


def test_extract_default_entity_is_calendar_year() -> None:
    grid = grid_from_rows(
        "PnL", [["Particulars", "Jul 2023"], ["Revenue", 1000], ["Cost of Sales", 600]]
    )
    stmt = extract_from_grid(grid, options=ExtractOptions())
    assert stmt.entity.company_name == "Your Company"
    assert stmt.periods[0].meta.fiscal_year == 2023
    assert stmt.periods[0].meta.sub_index == 7


def test_extract_messy_labels_mapped() -> None:
    grid = grid_from_rows(
        "PnL",
        [
            ["Particulars", "FY2023-24"],
            ["Turnover", 1000],
            ["Cost of Sales", 600],
            ["Financial Expenses", 50],
        ],
    )
    p = extract_from_grid(grid, options=ExtractOptions()).periods[0]
    assert p.revenue == Decimal("1000")
    assert p.cogs == Decimal("600")
    assert p.finance_cost == Decimal("50")


def test_extract_applies_scale() -> None:
    grid = grid_from_rows(
        "PnL",
        [["Amounts in '000"], ["Particulars", "FY2023-24"], ["Revenue", 1234], ["COGS", 1000]],
    )
    p = extract_from_grid(grid, options=ExtractOptions()).periods[0]
    assert p.revenue == Decimal("1234000")


def test_extract_scale_override() -> None:
    grid = grid_from_rows(
        "PnL",
        [["Figures in crore"], ["Particulars", "FY2023-24"], ["Revenue", 100], ["COGS", 60]],
    )
    p = extract_from_grid(grid, options=ExtractOptions(scale=Decimal("1"))).periods[0]
    assert p.revenue == Decimal("100")


def test_extract_missing_revenue_raises() -> None:
    grid = grid_from_rows("PnL", [["Particulars", "FY2023-24"], ["Cost of Sales", 600]])
    with pytest.raises(MissingRequiredLineError) as ei:
        extract_from_grid(grid, options=ExtractOptions())
    assert ei.value.line == "revenue"


def test_extract_missing_cogs_raises() -> None:
    grid = grid_from_rows("PnL", [["Particulars", "FY2023-24"], ["Revenue", 1000]])
    with pytest.raises(MissingRequiredLineError) as ei:
        extract_from_grid(grid, options=ExtractOptions())
    assert ei.value.line == "cogs"


def test_extract_volume_optional_default() -> None:
    grid = grid_from_rows("PnL", [["Particulars", "FY2023-24"], ["Revenue", 1000], ["COGS", 600]])
    assert extract_from_grid(grid, options=ExtractOptions()).periods[0].volume_mt is None


def test_extract_require_volume_flag() -> None:
    grid = grid_from_rows("PnL", [["Particulars", "FY2023-24"], ["Revenue", 1000], ["COGS", 600]])
    with pytest.raises(MissingRequiredLineError) as ei:
        extract_from_grid(grid, options=ExtractOptions(require_volume=True))
    assert ei.value.line == "volume_mt"


def test_extract_volume_not_scaled() -> None:
    grid = grid_from_rows(
        "PnL",
        [
            ["Amounts in '000"],
            ["Particulars", "FY2023-24"],
            ["Revenue", 1000],
            ["COGS", 600],
            ["Sales Volume (MT)", 1850],
        ],
    )
    p = extract_from_grid(grid, options=ExtractOptions()).periods[0]
    assert p.revenue == Decimal("1000000")  # scaled
    assert p.volume_mt == Decimal("1850")  # MT not scaled


def test_extract_unknown_lines_go_to_extra_lines() -> None:
    grid = grid_from_rows(
        "PnL",
        [
            ["Particulars", "FY2023-24"],
            ["Revenue", 1000],
            ["COGS", 600],
            ["Donations to charity", 5],
        ],
    )
    p = extract_from_grid(grid, options=ExtractOptions()).periods[0]
    assert len(p.extra_lines) == 1
    assert p.extra_lines[0].raw_label == "Donations to charity"
    assert p.extra_lines[0].source_ref == "B4"


def test_extract_opex_items_preserved() -> None:
    grid = grid_from_rows(
        "PnL",
        [
            ["Particulars", "FY2023-24"],
            ["Revenue", 1000],
            ["COGS", 600],
            ["Administrative Expenses", 80],
        ],
    )
    p = extract_from_grid(grid, options=ExtractOptions()).periods[0]
    assert p.opex.administrative == Decimal("80")
    assert len(p.opex.items) == 1
    assert p.opex.items[0].category == "administrative"
    assert p.opex.items[0].source_ref == "B4"


def test_extract_records_source_provenance() -> None:
    grid = grid_from_rows("PnL", [["Particulars", "FY2023-24"], ["Revenue", 1000], ["COGS", 600]])
    src = SourceMeta(source_file="x.xlsx", sheet_name="PnL")
    stmt = extract_from_grid(grid, options=ExtractOptions(), source=src)
    assert stmt.source is not None
    assert stmt.source.source_file == "x.xlsx"


def test_extract_pure_core_no_file() -> None:
    grid = grid_from_rows("PnL", [["Particulars", "FY2023-24"], ["Revenue", 1000], ["COGS", 600]])
    stmt = extract_from_grid(grid, options=ExtractOptions(), source=None)
    assert stmt.source is None
