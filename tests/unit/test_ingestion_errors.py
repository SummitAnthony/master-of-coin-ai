"""Tests for the typed ingestion error hierarchy and the package façade."""

from __future__ import annotations

from pathlib import Path

from advisor.ingestion.errors import (
    AmbiguousLabelError,
    CellParseError,
    IngestionError,
    MissingRequiredLineError,
    NoPeriodsFoundError,
    PeriodDetectionError,
    SheetNotFoundError,
    WorkbookReadError,
)


def test_all_errors_subclass_ingestionerror() -> None:
    for cls in (
        WorkbookReadError,
        SheetNotFoundError,
        PeriodDetectionError,
        NoPeriodsFoundError,
        MissingRequiredLineError,
        AmbiguousLabelError,
        CellParseError,
    ):
        assert issubclass(cls, IngestionError)


def test_sheetnotfound_carries_context() -> None:
    err = SheetNotFoundError("Nope", ["A", "B"])
    assert err.requested == "Nope"
    assert err.available == ["A", "B"]


def test_missingrequiredline_carries_context() -> None:
    err = MissingRequiredLineError("revenue", "FY2023-24")
    assert err.line == "revenue"
    assert err.period_label == "FY2023-24"


def test_cellparseerror_carries_context() -> None:
    err = CellParseError("junk", "C3")
    assert err.raw == "junk"
    assert err.coord == "C3"


def test_workbookreaderror_carries_context() -> None:
    err = WorkbookReadError(Path("x.xlsx"), "bad zip")
    assert err.path == Path("x.xlsx")
    assert err.reason == "bad zip"


def test_public_api_exports_errors() -> None:
    from advisor import ingestion

    for name in (
        "extract_income_statement",
        "extract_from_grid",
        "ExtractOptions",
        "IngestionError",
        "WorkbookReadError",
        "SheetNotFoundError",
        "CellParseError",
    ):
        assert name in ingestion.__all__
        assert hasattr(ingestion, name)
