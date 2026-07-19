"""Deterministic Decimal primitives shared by the engine.

Explicit ROUND_HALF_UP quantizers, division guards that return ``None`` for a
missing/non-positive denominator, and a sign->Direction helper with an epsilon
flat band. Pure: imports only ``decimal`` and the schema enums.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from advisor.schema import Direction

MONEY_QUANT: Final[Decimal] = Decimal("0.01")
PCT_QUANT: Final[Decimal] = Decimal("0.0001")
PER_MT_QUANT: Final[Decimal] = Decimal("0.01")
EPSILON: Final[Decimal] = Decimal("0.0001")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def quantize_pct(value: Decimal) -> Decimal:
    return value.quantize(PCT_QUANT, rounding=ROUND_HALF_UP)


def quantize_per_mt(value: Decimal) -> Decimal:
    return value.quantize(PER_MT_QUANT, rounding=ROUND_HALF_UP)


def safe_div(numerator: Decimal, denominator: Decimal | None, quant: Decimal) -> Decimal | None:
    """Return numerator/denominator quantized, or None if denominator <= 0/None."""
    if denominator is None or denominator <= 0:
        return None
    return (numerator / denominator).quantize(quant, rounding=ROUND_HALF_UP)


def pct_of(part: Decimal, whole: Decimal | None) -> Decimal | None:
    """Return part/whole*100 (percentage points), or None if whole <= 0/None."""
    if whole is None or whole <= 0:
        return None
    return (part / whole * 100).quantize(PCT_QUANT, rounding=ROUND_HALF_UP)


def per_mt(amount: Decimal, volume_mt: Decimal | None) -> Decimal | None:
    """Return amount/volume (money per volume unit), or None if volume <= 0/None."""
    return safe_div(amount, volume_mt, PER_MT_QUANT)


def direction_of(delta: Decimal | None, epsilon: Decimal = EPSILON) -> Direction:
    """Map a change to a Direction; |delta| <= epsilon (or None) is FLAT."""
    if delta is None or abs(delta) <= epsilon:
        return Direction.FLAT
    return Direction.UP if delta > 0 else Direction.DOWN
