"""Ingestion layer (PURE).

Reads income statements and maps them onto the canonical schema.
No network access and no LLM imports (openpyxl is confined to ``workbook.py``).
Enforced by an architecture test.
"""

from __future__ import annotations

from .errors import (
    AmbiguousLabelError,
    CellParseError,
    IngestionError,
    MissingRequiredLineError,
    NoPeriodsFoundError,
    PeriodDetectionError,
    SheetNotFoundError,
    WorkbookReadError,
)
from .extractor import ExtractOptions, extract_from_grid, extract_income_statement

__all__ = [
    "AmbiguousLabelError",
    "CellParseError",
    "ExtractOptions",
    "IngestionError",
    "MissingRequiredLineError",
    "NoPeriodsFoundError",
    "PeriodDetectionError",
    "SheetNotFoundError",
    "WorkbookReadError",
    "extract_from_grid",
    "extract_income_statement",
]
