"""Deterministic mapping from messy human labels to canonical line keys.

This is parsing logic (not user-tunable thresholds), so it lives in code, but
the synonym table is plain data for easy extension. Exact-normalized matches are
preferred over substring matches to minimise false ambiguity.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final

from .errors import AmbiguousLabelError


class LineKey(StrEnum):
    """Canonical income-statement line identifiers."""

    REVENUE = "revenue"
    COGS = "cogs"
    GROSS_PROFIT = "gross_profit"
    OPERATING_PROFIT = "operating_profit"
    OTHER_INCOME = "other_income"
    FINANCE_COST = "finance_cost"
    PROFIT_BEFORE_TAX = "profit_before_tax"
    TAX_EXPENSE = "tax_expense"
    NET_PROFIT = "net_profit"
    VOLUME_MT = "volume_mt"
    OPEX_SELLING_DISTRIBUTION = "opex_selling_distribution"
    OPEX_ADMINISTRATIVE = "opex_administrative"
    OPEX_OTHER = "opex_other"
    OPEX_TOTAL = "opex_total"


ALIASES: Final[dict[LineKey, tuple[str, ...]]] = {
    LineKey.REVENUE: (
        "revenue",
        "net sales",
        "turnover",
        "sales",
        "net turnover",
        "gross sales",
        "net revenue",
    ),
    LineKey.COGS: (
        "cost of goods sold",
        "cost of sales",
        "cogs",
        "cost of production",
        "cost of revenue",
    ),
    LineKey.GROSS_PROFIT: ("gross profit", "gross margin"),
    LineKey.OPERATING_PROFIT: (
        "operating profit",
        "operating income",
        "profit from operations",
        "ebit",
    ),
    LineKey.OTHER_INCOME: ("other income", "non operating income"),
    LineKey.FINANCE_COST: (
        "finance cost",
        "finance costs",
        "financial expenses",
        "financial expense",
        "interest expense",
        "bank interest",
    ),
    LineKey.PROFIT_BEFORE_TAX: (
        "profit before tax",
        "pbt",
        "profit before taxation",
        "net profit before tax",
    ),
    LineKey.TAX_EXPENSE: (
        "tax expense",
        "income tax",
        "income tax expense",
        "provision for tax",
        "tax",
    ),
    LineKey.NET_PROFIT: (
        "net profit",
        "profit after tax",
        "pat",
        "net profit after tax",
        "profit for the year",
        "net income",
    ),
    LineKey.VOLUME_MT: (
        "sales volume",
        "sales volume mt",
        "volume mt",
        "quantity sold",
        "sales quantity",
    ),
    LineKey.OPEX_SELLING_DISTRIBUTION: (
        "selling and distribution expenses",
        "selling and distribution",
        "selling expenses",
        "distribution expenses",
    ),
    LineKey.OPEX_ADMINISTRATIVE: (
        "administrative expenses",
        "admin expenses",
        "general and administrative expenses",
        "administration expenses",
    ),
    LineKey.OPEX_OTHER: ("other operating expenses", "other opex"),
    LineKey.OPEX_TOTAL: (
        "total operating expenses",
        "operating expenses",
        "total opex",
        "total operating expense",
    ),
}

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def normalize_label(raw: str) -> str:
    """Casefold, strip, drop punctuation/footnotes, and collapse whitespace."""
    s = raw.casefold().strip()
    s = s.replace("&", " and ")
    s = _PUNCT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


# Precompute normalized alias -> key for exact lookups.
_EXACT: Final[dict[str, LineKey]] = {
    normalize_label(alias): key for key, aliases in ALIASES.items() for alias in aliases
}


def match_line(raw: str, *, coord: str | None = None) -> LineKey | None:
    """Map a label to its canonical :class:`LineKey`, or None if unrecognised.

    Raises :class:`AmbiguousLabelError` only when ``coord`` is supplied and the
    label matches more than one distinct key.
    """
    norm = normalize_label(raw)
    if not norm:
        return None
    exact = _EXACT.get(norm)
    if exact is not None:
        return exact
    hits: set[LineKey] = set()
    for alias_norm, key in _EXACT.items():
        if alias_norm in norm or norm in alias_norm:
            hits.add(key)
    if len(hits) == 1:
        return next(iter(hits))
    if len(hits) > 1 and coord is not None:
        raise AmbiguousLabelError(raw, sorted(k.value for k in hits), coord)
    return None
