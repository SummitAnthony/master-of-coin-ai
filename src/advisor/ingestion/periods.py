"""Detect period columns and parse their headers into PeriodMeta (pure).

Assigns a canonical sequence (oldest = 0) from the parsed fiscal year /
sub-index, independent of the spreadsheet's column order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from ..schema import PeriodMeta, PeriodType
from .errors import NoPeriodsFoundError, PeriodDetectionError


@dataclass(frozen=True)
class PeriodColumn:
    """A spreadsheet column identified as a reporting period."""

    col_index: int
    meta: PeriodMeta


_MONTHS: Final[dict[str, int]] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

_Q_RE = re.compile(r"\bq([1-4])\b")
_H_RE = re.compile(r"\bh([12])\b")


def _fy_and_subindex_for_month(cal_year: int, cal_month: int, fy_end_month: int) -> tuple[int, int]:
    start_month = (fy_end_month % 12) + 1
    sub = ((cal_month - start_month) % 12) + 1
    fy = cal_year + 1 if cal_month > fy_end_month else cal_year
    return fy, sub


def _extract_fy(s: str) -> int | None:
    m = re.search(r"fy\s*'?(\d{4})\s*[-/]\s*'?(\d{2,4})", s)
    if m:
        end = m.group(2)
        return int(end) if len(end) == 4 else 2000 + int(end)
    m = re.search(r"fy\s*'?(\d{4})", s)
    if m:
        return int(m.group(1))
    m = re.search(r"fy\s*'?(\d{2})\b", s)
    if m:
        return 2000 + int(m.group(1))
    m = re.search(r"\b(\d{4})\s*[-/]\s*'?(\d{2,4})\b", s)
    if m:
        end = m.group(2)
        return int(end) if len(end) == 4 else 2000 + int(end)
    m = re.search(r"\b(\d{4})\b", s)
    if m:
        return int(m.group(1))
    return None


def parse_period_label(label: str, *, fiscal_year_end_month: int) -> PeriodMeta:
    """Parse a header label into a :class:`PeriodMeta` (sequence left as 0)."""
    raw = label.strip()
    s = raw.casefold()
    if not s:
        raise PeriodDetectionError(label, "empty label")

    for name, month in _MONTHS.items():
        if re.search(rf"\b{name}\b", s):
            ym = re.search(r"(\d{4})", s)
            if ym is None:
                raise PeriodDetectionError(label, "month without a year")
            month_fy, sub = _fy_and_subindex_for_month(
                int(ym.group(1)), month, fiscal_year_end_month
            )
            return PeriodMeta(
                label=raw,
                period_type=PeriodType.MONTH,
                fiscal_year=month_fy,
                sequence=0,
                sub_index=sub,
                months=1,
            )

    q = _Q_RE.search(s)
    if q:
        fy = _extract_fy(s)
        if fy is None:
            raise PeriodDetectionError(label, "quarter without a year")
        return PeriodMeta(
            label=raw,
            period_type=PeriodType.QUARTER,
            fiscal_year=fy,
            sequence=0,
            sub_index=int(q.group(1)),
            months=3,
        )

    h = _H_RE.search(s)
    if h:
        fy = _extract_fy(s)
        if fy is None:
            raise PeriodDetectionError(label, "half without a year")
        return PeriodMeta(
            label=raw,
            period_type=PeriodType.HALF,
            fiscal_year=fy,
            sequence=0,
            sub_index=int(h.group(1)),
            months=6,
        )

    fy = _extract_fy(s)
    if fy is not None:
        return PeriodMeta(
            label=raw,
            period_type=PeriodType.YEAR,
            fiscal_year=fy,
            sequence=0,
            sub_index=None,
            months=12,
        )

    raise PeriodDetectionError(label, "unrecognised period format")


def detect_period_columns(
    header_cells: list[tuple[int, object]],
    *,
    fiscal_year_end_month: int,
    sheet: str = "?",
) -> list[PeriodColumn]:
    """Identify period columns from a header row, ordered oldest-first.

    Non-period cells (label column, notes, blanks) are silently skipped.
    Raises :class:`NoPeriodsFoundError` if no period columns survive.
    """
    found: list[tuple[int, PeriodMeta]] = []
    for col_index, value in header_cells:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        try:
            meta = parse_period_label(text, fiscal_year_end_month=fiscal_year_end_month)
        except PeriodDetectionError:
            continue
        found.append((col_index, meta))

    if not found:
        raise NoPeriodsFoundError(sheet)

    found.sort(key=lambda cm: (cm[1].fiscal_year, cm[1].sub_index or 0, cm[0]))
    return [
        PeriodColumn(col_index=col_index, meta=meta.model_copy(update={"sequence": seq}))
        for seq, (col_index, meta) in enumerate(found)
    ]
