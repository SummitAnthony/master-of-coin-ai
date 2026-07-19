"""Tests for prompt template loading and rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from advisor.narrative.context import build_context
from advisor.narrative.templates import DEFAULT_TEMPLATES, load_templates, render, render_system
from advisor.schema import Facts


def test_load_default_templates() -> None:
    t = load_templates()
    assert t is DEFAULT_TEMPLATES
    assert t.system and t.executive_summary and t.risk_commentary and t.recommendations


def test_load_yaml_override(tmp_path: Path) -> None:
    path = tmp_path / "p.yaml"
    path.write_text(
        "system: S\nexecutive_summary: E {facts}\nrisk_commentary: R\nrecommendations: C\n",
        encoding="utf-8",
    )
    assert load_templates(path).executive_summary == "E {facts}"


def test_load_invalid_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- not a mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_templates(path)


def test_render_injects_facts_block(facts: Facts) -> None:
    ctx = build_context(facts)
    out = render(DEFAULT_TEMPLATES.executive_summary, ctx)
    assert ctx.as_prompt_block() in out
    assert "{facts}" not in out


def test_render_normalises_crlf(facts: Facts) -> None:
    ctx = build_context(facts)
    assert "\r\n" not in render("line1\r\nline2 {facts}", ctx)


def test_render_system_substitutes_company_profile(facts: Facts) -> None:
    ctx = build_context(facts)
    out = render_system(DEFAULT_TEMPLATES.system, ctx)
    assert "{company}" not in out
    assert "{currency}" not in out
    assert "{volume_unit}" not in out
    assert ctx.company_name in out
    assert ctx.currency in out
    assert ctx.volume_unit in out


def test_default_templates_are_company_neutral() -> None:
    t = DEFAULT_TEMPLATES
    for text in (t.system, t.executive_summary, t.risk_commentary, t.recommendations):
        assert "AOPL" not in text
        assert "Anwar" not in text
        assert "A1 Polymer" not in text
