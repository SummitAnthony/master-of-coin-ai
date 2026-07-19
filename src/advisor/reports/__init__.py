"""Report generators: enhanced Excel, PDF board note, Word memo, dashboard payload."""

from __future__ import annotations

from .dashboard import build_dashboard_payload, write_dashboard_json
from .excel import build_workbook, write_excel
from .pack import ReportPack, generate_report_pack
from .pdf import build_pdf_bytes, write_pdf
from .word import build_document, write_word

__all__ = [
    "ReportPack",
    "build_dashboard_payload",
    "build_document",
    "build_pdf_bytes",
    "build_workbook",
    "generate_report_pack",
    "write_dashboard_json",
    "write_excel",
    "write_pdf",
    "write_word",
]
