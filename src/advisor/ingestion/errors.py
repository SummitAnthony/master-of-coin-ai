"""Typed ingestion errors carrying machine-readable context.

Callers (API/UI in later milestones) get structured failures instead of
stack traces. Every error stores its context as attributes, not just a string.
"""

from __future__ import annotations

from pathlib import Path


class IngestionError(Exception):
    """Base class for all ingestion failures."""


class WorkbookReadError(IngestionError):
    """The file could not be opened as an .xlsx workbook."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Could not read workbook '{path}': {reason}")


class SheetNotFoundError(IngestionError):
    """The requested sheet name does not exist in the workbook."""

    def __init__(self, requested: str, available: list[str]) -> None:
        self.requested = requested
        self.available = available
        super().__init__(f"Sheet '{requested}' not found; available: {available}")


class PeriodDetectionError(IngestionError):
    """A header label could not be parsed into a reporting period."""

    def __init__(self, label: str, reason: str) -> None:
        self.label = label
        self.reason = reason
        super().__init__(f"Could not parse period header '{label}': {reason}")


class NoPeriodsFoundError(IngestionError):
    """No period columns were detected in the sheet."""

    def __init__(self, sheet: str) -> None:
        self.sheet = sheet
        super().__init__(f"No period columns detected in sheet '{sheet}'")


class MissingRequiredLineError(IngestionError):
    """A required line (revenue/cogs/...) is absent for a period."""

    def __init__(self, line: str, period_label: str) -> None:
        self.line = line
        self.period_label = period_label
        super().__init__(f"Required line '{line}' missing for period '{period_label}'")


class AmbiguousLabelError(IngestionError):
    """One row label matched more than one canonical line key."""

    def __init__(self, raw_label: str, candidates: list[str], coord: str) -> None:
        self.raw_label = raw_label
        self.candidates = candidates
        self.coord = coord
        super().__init__(f"Label '{raw_label}' at {coord} matches multiple keys: {candidates}")


class CellParseError(IngestionError):
    """A non-empty cell could not be parsed as a monetary amount."""

    def __init__(self, raw: object, coord: str) -> None:
        self.raw = raw
        self.coord = coord
        super().__init__(f"Could not parse amount {raw!r} at {coord}")
