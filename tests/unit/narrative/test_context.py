"""Tests for the prompt-safe NarrativeContext."""

from __future__ import annotations

from advisor.narrative.context import build_context
from advisor.schema import Facts


def test_build_context_mirrors_facts(facts: Facts) -> None:
    ctx = build_context(facts)
    assert ctx.currency == "USD"
    assert ctx.volume_unit == "MT"
    assert ctx.period_labels == [p.label for p in facts.periods]
    assert ctx.latest_period == facts.latest_period.label
    assert len(ctx.kpis) == len(facts.kpis)
    assert ctx.variances  # 2 periods -> sequential variances exist


def test_context_excludes_raw_inputs(facts: Facts) -> None:
    block = build_context(facts).as_prompt_block()
    for forbidden in ("raw_label", "source_ref", "extra_lines", "PnL!"):
        assert forbidden not in block


def test_as_prompt_block_is_deterministic(facts: Facts) -> None:
    ctx = build_context(facts)
    assert ctx.as_prompt_block() == ctx.as_prompt_block()


def test_decimals_serialized_as_strings(facts: Facts) -> None:
    ctx = build_context(facts)
    assert all(isinstance(row["revenue"], str) for row in ctx.kpis)
