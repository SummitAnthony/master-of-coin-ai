"""Thin orchestrator that runs all four report generators (used by the API)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from advisor.narrative.advisor import Advisory
from advisor.schema import Facts, IncomeStatement

from .dashboard import write_dashboard_json
from .excel import write_excel
from .pdf import write_pdf
from .word import write_word


@dataclass(frozen=True)
class ReportPack:
    """Paths to the four generated artifacts."""

    excel_path: Path
    pdf_path: Path
    word_path: Path
    dashboard_path: Path


def generate_report_pack(
    facts: Facts,
    narrative: Advisory,
    out_dir: Path,
    *,
    generated_at: datetime,
    statement: IncomeStatement | None = None,
    stem: str = "advisory",
) -> ReportPack:
    """Generate Excel, PDF, Word and dashboard JSON into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    return ReportPack(
        excel_path=write_excel(
            facts,
            narrative,
            out_dir / f"{stem}.xlsx",
            generated_at=generated_at,
            statement=statement,
        ),
        pdf_path=write_pdf(facts, narrative, out_dir / f"{stem}.pdf", generated_at=generated_at),
        word_path=write_word(facts, narrative, out_dir / f"{stem}.docx", generated_at=generated_at),
        dashboard_path=write_dashboard_json(
            facts, narrative, out_dir / f"{stem}.json", generated_at=generated_at
        ),
    )
