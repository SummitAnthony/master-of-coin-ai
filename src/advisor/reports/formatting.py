"""Deterministic formatters and the report theme.

Pure and side-effect-free. Inputs are Decimal (or None); passing a float raises
TypeError so golden output never drifts on binary float repr. Currency and
volume unit are parameters (defaults match ``EntityMeta``); ``grouping``
selects western (1,234,567) or south-asian (12,34,567) digit grouping.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final, Literal

from advisor.schema import Direction, Status

NA: Final[str] = "n/a"
DEFAULT_CURRENCY: Final[str] = "USD"
DEFAULT_VOLUME_UNIT: Final[str] = "MT"
DISCLAIMER: Final[str] = (
    "Figures are computed deterministically by the analytics engine and are reproducible; "
    "the narrative is advisory commentary only."
)

BRAND_PRIMARY_HEX: Final[str] = "1F4E79"  # deep blue report theme
BRAND_ACCENT_HEX: Final[str] = "C00000"
STATUS_HEX: Final[dict[Status, str]] = {
    Status.GREEN: "2E7D32",
    Status.YELLOW: "F9A825",
    Status.RED: "C62828",
    Status.UNKNOWN: "9E9E9E",
}
DIRECTION_SYMBOL: Final[dict[Direction, str]] = {
    Direction.UP: "^",
    Direction.DOWN: "v",
    Direction.FLAT: "-",
}
SHEET_NAMES: Final[tuple[str, ...]] = (
    "Cover",
    "Income Statement",
    "KPIs",
    "Variance",
    "Status",
    "Anomalies",
)

Grouping = Literal["western", "south_asian"]


def _require_decimal(value: Decimal | None) -> None:
    if value is not None and not isinstance(value, Decimal):
        raise TypeError("formatters accept Decimal or None only")


def _group_south_asian(int_digits: str) -> str:
    if len(int_digits) <= 3:
        return int_digits
    head, tail = int_digits[:-3], int_digits[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def _quantized(value: Decimal, decimals: int) -> Decimal:
    quant = Decimal(1) if decimals == 0 else Decimal(1).scaleb(-decimals)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


def _grouped(value: Decimal, grouping: Grouping) -> str:
    if grouping == "western":
        return f"{value:,f}"
    text = f"{value:f}"
    int_part, _, frac = text.partition(".")
    return _group_south_asian(int_part) + (f".{frac}" if frac else "")


def format_money(
    value: Decimal | None,
    *,
    currency: str = DEFAULT_CURRENCY,
    decimals: int = 0,
    grouping: Grouping = "western",
) -> str:
    _require_decimal(value)
    if value is None:
        return NA
    negative = value < 0
    body = f"{currency} {_grouped(_quantized(abs(value), decimals), grouping)}"
    return f"({body})" if negative else body


def format_pct(value: Decimal | None, *, decimals: int = 2) -> str:
    _require_decimal(value)
    if value is None:
        return NA
    return f"{_quantized(value, decimals):f}%"


def format_volume(
    value: Decimal | None, *, unit: str = DEFAULT_VOLUME_UNIT, decimals: int = 2
) -> str:
    _require_decimal(value)
    if value is None:
        return NA
    return f"{_quantized(value, decimals):,f} {unit}"


def format_per_unit(
    value: Decimal | None,
    *,
    currency: str = DEFAULT_CURRENCY,
    unit: str = DEFAULT_VOLUME_UNIT,
    decimals: int = 2,
) -> str:
    _require_decimal(value)
    if value is None:
        return NA
    return f"{currency} {_quantized(value, decimals):,f} /{unit}"


def format_bps(value: Decimal | None) -> str:
    _require_decimal(value)
    if value is None:
        return NA
    rounded = _quantized(value, 0)
    sign = "+" if rounded >= 0 else ""
    return f"{sign}{rounded:f} bps"


def status_hex(status: Status) -> str:
    return STATUS_HEX[status]


def direction_symbol(direction: Direction) -> str:
    return DIRECTION_SYMBOL[direction]


def excel_number_format(
    kind: Literal["money", "pct", "volume", "per_unit"],
    *,
    currency: str = DEFAULT_CURRENCY,
    unit: str = DEFAULT_VOLUME_UNIT,
) -> str:
    return {
        "money": f'"{currency} "#,##0',
        "pct": '0.00"%"',
        "volume": f'#,##0.00" {unit}"',
        "per_unit": f'"{currency} "#,##0.00" /{unit}"',
    }[kind]
