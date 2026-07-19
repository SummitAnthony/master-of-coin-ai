"""Detect the reporting scale from header text and return a Decimal multiplier.

Converts reported figures to absolute amounts (e.g. "in '000" -> x1000). An explicit
caller override always wins. Never raises: defaults to x1 when nothing matches.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Final

# Ordered longest/most-specific first so ambiguous text resolves deterministically.
SCALE_KEYWORDS: Final[tuple[tuple[str, Decimal], ...]] = (
    ("crore", Decimal("10000000")),
    ("million", Decimal("1000000")),
    ("lakh", Decimal("100000")),
    ("lac", Decimal("100000")),
    ("mn", Decimal("1000000")),
    ("'000", Decimal("1000")),
    ("in 000", Decimal("1000")),
    ("thousand", Decimal("1000")),
)


def detect_scale(header_texts: Iterable[str], *, override: Decimal | None = None) -> Decimal:
    """Return the multiplier to absolute amounts; ``override`` takes precedence."""
    if override is not None:
        return override
    blob = " ".join(t.casefold() for t in header_texts if t)
    for keyword, multiplier in SCALE_KEYWORDS:
        if keyword in blob:
            return multiplier
    return Decimal("1")
