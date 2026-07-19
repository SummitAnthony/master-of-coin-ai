"""End-to-end: planted raw inputs in the statement never reach the LLM prompt."""

from __future__ import annotations

from decimal import Decimal

from advisor.engine.facts import build_facts
from advisor.narrative.advisor import advisor
from advisor.schema import (
    IncomeStatement,
    LineItem,
    OperatingExpenses,
    Period,
    PeriodMeta,
    PeriodType,
)

D = Decimal
_RAW_LABEL = "ZZZ_RAW_LABEL"
_SOURCE_REF = "PnL!C14"
THRESHOLDS = {
    "margins": {"gross_margin_pct": {"green": 18, "yellow": 12, "direction": "higher_is_better"}},
    "ratios": {},
    "anomalies": {},
}


class _Recorder:
    provider = "mock"
    model = "m"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append(prompt)
        return "ok"


def _statement_with_raw() -> IncomeStatement:
    return IncomeStatement(
        periods=[
            Period(
                meta=PeriodMeta(
                    label="FY2023-24", period_type=PeriodType.YEAR, fiscal_year=2024, sequence=0
                ),
                revenue=D("2480"),
                cogs=D("1910"),
                opex=OperatingExpenses(
                    items=[
                        LineItem(
                            label="Misc",
                            amount=D("5"),
                            raw_label=_RAW_LABEL,
                            source_ref=_SOURCE_REF,
                        )
                    ]
                ),
                extra_lines=[
                    LineItem(
                        label="Note",
                        amount=D("3"),
                        raw_label=_RAW_LABEL,
                        source_ref=_SOURCE_REF,
                    )
                ],
                volume_mt=D("18"),
            )
        ]
    )


def test_facts_to_narrative_no_leak() -> None:
    facts = build_facts(_statement_with_raw(), thresholds=THRESHOLDS)
    recorder = _Recorder()
    advisor(facts, client=recorder)
    assert recorder.calls  # prompts were sent
    joined = "\n".join(recorder.calls)
    assert "2480" in joined  # a real KPI figure made it through
    assert _RAW_LABEL not in joined
    assert _SOURCE_REF not in joined


def test_full_advisory_serialises() -> None:
    facts = build_facts(_statement_with_raw(), thresholds=THRESHOLDS)
    result = advisor(facts, client=_Recorder())
    assert result.model_dump(mode="json")["provider"] == "mock"
