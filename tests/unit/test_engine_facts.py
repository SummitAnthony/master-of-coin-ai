"""Tests for Facts assembly, reproducibility, and the trust boundary."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

import advisor.schema as schema
from advisor.engine.facts import ENGINE_VERSION, build_facts
from advisor.schema import Facts, IncomeStatement, Period, PeriodMeta, PeriodType

D = Decimal

THRESHOLDS = {
    "margins": {
        "gross_margin_pct": {"green": 18, "yellow": 12, "direction": "higher_is_better"},
        "operating_margin_pct": {"green": 10, "yellow": 5, "direction": "higher_is_better"},
        "net_margin_pct": {"green": 6, "yellow": 2, "direction": "higher_is_better"},
    },
    "ratios": {
        "finance_cost_to_sales_pct": {"green": 3, "yellow": 6, "direction": "lower_is_better"},
        "opex_to_sales_pct": {"green": 8, "yellow": 12, "direction": "lower_is_better"},
    },
    "anomalies": {
        "margin_drop_bps": 200,
        "cogs_vs_sales_growth_gap_pct": 3.0,
        "cost_spike_pct": 15.0,
    },
}


def _period(seq: int, label: str, rev: str, cogs: str, fy: int) -> Period:
    return Period(
        meta=PeriodMeta(label=label, period_type=PeriodType.YEAR, fiscal_year=fy, sequence=seq),
        revenue=D(rev),
        cogs=D(cogs),
    )


def _stmt() -> IncomeStatement:
    return IncomeStatement(
        periods=[
            _period(0, "FY2022-23", "2200000000", "1720000000", 2023),
            _period(1, "FY2023-24", "2480000000", "1910000000", 2024),
        ]
    )


def test_build_facts_structure() -> None:
    facts = build_facts(_stmt(), thresholds=THRESHOLDS)
    assert facts.engine_version == ENGINE_VERSION
    assert [p.sequence for p in facts.periods] == [0, 1]
    assert facts.latest_period == facts.periods[-1]
    assert len(facts.kpis) == 2
    assert len(facts.statuses) == 2 * 5  # 2 periods x 5 threshold rules
    assert facts.variances  # sequential variances present


def test_build_facts_is_reproducible() -> None:
    a = build_facts(_stmt(), thresholds=THRESHOLDS)
    b = build_facts(_stmt(), thresholds=THRESHOLDS)
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_build_facts_json_roundtrip() -> None:
    facts = build_facts(_stmt(), thresholds=THRESHOLDS)
    assert Facts.model_validate(facts.model_dump(mode="json")) == facts


def test_build_facts_default_thresholds_loads_yaml() -> None:
    # thresholds=None -> reads config/thresholds.yaml (absolute path, offline).
    facts = build_facts(_stmt())
    assert isinstance(facts, Facts)


def _all_keys(obj: object) -> Iterator[str]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _all_keys(value)


def test_facts_contains_no_raw_provenance() -> None:
    facts = build_facts(_stmt(), thresholds=THRESHOLDS)
    keys = set(_all_keys(facts.model_dump(mode="json")))
    assert keys.isdisjoint({"raw_label", "source_ref", "extra_lines", "items"})


def test_facts_models_embed_no_raw_containers() -> None:
    forbidden = ("IncomeStatement", "LineItem", "OperatingExpenses", "SourceMeta")
    for model in (
        schema.Facts,
        schema.PeriodKPIs,
        schema.PeriodRef,
        schema.Variance,
        schema.KpiStatus,
        schema.Anomaly,
    ):
        for name, field in model.model_fields.items():
            annotation = str(field.annotation)
            for bad in forbidden:
                assert bad not in annotation, f"{model.__name__}.{name} references {bad}"
