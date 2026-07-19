"""Integration tests exercising the real openpyxl read path in workbook.load_grid."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from advisor.ingestion import (
    ExtractOptions,
    NoPeriodsFoundError,
    SheetNotFoundError,
    WorkbookReadError,
    extract_income_statement,
)

_CLEAN_ROWS: list[list[object]] = [
    ["A1 Polymer Ltd. (Anwar Group of Industries)"],
    ["Statement of Profit or Loss for the year ended 30 June 2024"],
    ["Amounts in BDT"],
    ["Particulars", "FY2023-24"],
    ["Revenue (Net Sales)", 2480000000],
    ["Cost of Goods Sold", 1910000000],
    ["Gross Profit", 570000000],
    ["Selling & Distribution Expenses", 96000000],
    ["Administrative Expenses", 138000000],
    ["Other Operating Expenses", 22000000],
    ["Total Operating Expenses", 256000000],
    ["Operating Profit", 314000000],
    ["Other Income", 12500000],
    ["Finance Cost", 142000000],
    ["Profit Before Tax", 184500000],
    ["Income Tax Expense", 46125000],
    ["Net Profit", 138375000],
    ["Sales Volume (MT)", 18500],
]


def _write_xlsx(
    path: Path, rows: list[list[object]], sheet_title: str = "Income Statement"
) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def test_roundtrip_clean_workbook(tmp_path: Path) -> None:
    path = tmp_path / "clean.xlsx"
    _write_xlsx(path, _CLEAN_ROWS)
    stmt = extract_income_statement(path)
    assert len(stmt.periods) == 1
    p = stmt.periods[0]
    assert p.revenue == Decimal("2480000000")
    assert p.cogs == Decimal("1910000000")
    assert p.gross_profit == Decimal("570000000")
    assert p.opex.total == Decimal("256000000")
    assert p.net_profit == Decimal("138375000")
    assert p.volume_mt == Decimal("18500")
    assert stmt.source is not None
    assert stmt.source.source_scale == Decimal("1")


def test_roundtrip_multiperiod_workbook(tmp_path: Path) -> None:
    rows: list[list[object]] = [
        ["Particulars", "FY2021-22", "FY2022-23", "FY2023-24"],
        ["Revenue", 2000000000, 2200000000, 2480000000],
        ["Cost of Goods Sold", 1600000000, 1720000000, 1910000000],
    ]
    path = tmp_path / "multi.xlsx"
    _write_xlsx(path, rows)
    stmt = extract_income_statement(path)
    assert [p.meta.fiscal_year for p in stmt.periods] == [2022, 2023, 2024]
    assert [p.meta.sequence for p in stmt.periods] == [0, 1, 2]
    assert stmt.periods[-1].revenue == Decimal("2480000000")


def test_missing_sheet_raises(tmp_path: Path) -> None:
    path = tmp_path / "clean.xlsx"
    _write_xlsx(path, _CLEAN_ROWS)
    with pytest.raises(SheetNotFoundError) as ei:
        extract_income_statement(path, ExtractOptions(sheet="Nope"))
    assert "Income Statement" in ei.value.available


def test_corrupt_file_raises_workbookreaderror(tmp_path: Path) -> None:
    path = tmp_path / "broken.xlsx"
    path.write_bytes(b"this is not a real xlsx file")
    with pytest.raises(WorkbookReadError):
        extract_income_statement(path)


def test_nonexistent_path_raises_workbookreaderror(tmp_path: Path) -> None:
    with pytest.raises(WorkbookReadError):
        extract_income_statement(tmp_path / "does_not_exist.xlsx")


def test_empty_sheet_raises_noperiodsfound(tmp_path: Path) -> None:
    path = tmp_path / "empty.xlsx"
    _write_xlsx(path, [["Title only"]])
    with pytest.raises(NoPeriodsFoundError):
        extract_income_statement(path)


def test_file_handle_released_on_windows(tmp_path: Path) -> None:
    path = tmp_path / "clean.xlsx"
    _write_xlsx(path, _CLEAN_ROWS)
    extract_income_statement(path)
    path.unlink()  # would raise PermissionError on Windows if the handle leaked
    assert not path.exists()


def test_real_aopl_fixture_extracts() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "aopl_income_statement.xlsx"
    if not fixture.exists():
        pytest.skip("real AOPL fixture not provided")
    stmt = extract_income_statement(fixture)
    assert len(stmt.periods) >= 1
    assert all(p.revenue > 0 for p in stmt.periods)
