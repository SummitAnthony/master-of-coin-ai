"""Pure parsing of messy spreadsheet cell values into Decimal amounts.

Handles thousands separators, parentheses negatives, currency symbols, and
dash/blank placeholders deterministically. No float is ever produced.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Final

from .errors import CellParseError

_PLACEHOLDERS: Final[frozenset[str]] = frozenset({"-", "–", "—", "n/a", "na", ""})  # noqa: RUF001
# Currency markers and grouping characters stripped before parsing a string cell.
_STRIP_TOKENS: Final[tuple[str, ...]] = (
    "৳",
    "tk",
    "bdt",
    "$",
    "usd",
    "€",
    "eur",
    "£",
    "gbp",
    "₹",
    "inr",
    ",",
)


def is_blank(raw: object) -> bool:
    """True for None and dash/placeholder/whitespace-only strings."""
    if raw is None:
        return True
    if isinstance(raw, str):
        return raw.strip().casefold() in _PLACEHOLDERS
    return False


def parse_amount(raw: object, *, coord: str = "?") -> Decimal | None:
    """Parse a cell value into a Decimal, or None for a genuinely empty cell.

    Raises :class:`CellParseError` for a non-empty value that is not a number.
    """
    if is_blank(raw):
        return None
    if isinstance(raw, bool):
        # bool is an int subclass; reject so TRUE/FALSE never becomes 1/0.
        raise CellParseError(raw, coord)
    if isinstance(raw, int):
        return Decimal(raw)
    if isinstance(raw, float):
        return Decimal(str(raw))  # via str() to avoid binary-float artifacts
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, str):
        return _parse_str(raw, coord)
    raise CellParseError(raw, coord)


def _parse_str(text: str, coord: str) -> Decimal:
    s = text.strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    low = s.casefold()
    for token in _STRIP_TOKENS:
        low = low.replace(token, "")
    low = low.replace("mt", "").replace(" ", "")  # drop a stray MT unit + spaces
    if low in {"", "-"}:
        raise CellParseError(text, coord)
    try:
        value = Decimal(low)
    except InvalidOperation as exc:
        raise CellParseError(text, coord) from exc
    if not value.is_finite():
        raise CellParseError(text, coord)
    return -value if negative else value
