"""Tests for the downloadable blank input template (.xlsx)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from advisor.ingestion import extract_income_statement
from advisor.reports.template import build_input_template, write_input_template
from advisor.schema import EntityMeta


def test_template_sheets_and_headers() -> None:
    wb = build_input_template()
    assert wb.active is not None and wb.active.title == "Income Statement"
    assert "Instructions" in wb.sheetnames
    ws = wb["Income Statement"]
    labels = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    assert "Revenue" in labels
    assert "Cost of Goods Sold" in labels
    assert "Sales Volume" in labels


def test_template_mentions_configured_currency() -> None:
    wb = build_input_template(entity=EntityMeta(currency="BDT", volume_unit="MT"))
    ws = wb["Income Statement"]
    texts = [str(c.value) for row in ws.iter_rows() for c in row if c.value is not None]
    assert any("BDT" in t for t in texts)


def test_template_roundtrips_through_extraction(tmp_path: Path) -> None:
    path = write_input_template(tmp_path / "template.xlsx")
    stmt = extract_income_statement(path)
    assert len(stmt.periods) == 2
    latest = stmt.periods[-1]
    assert latest.revenue > Decimal("0")
    assert latest.cogs > Decimal("0")
    assert latest.gross_profit is not None
    assert latest.net_profit is not None
    assert latest.volume_mt is not None
    assert latest.opex.administrative is not None
