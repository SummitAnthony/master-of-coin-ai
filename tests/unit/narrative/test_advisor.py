"""Tests for the advisor() orchestrator: sections, trust, fail-soft."""

from __future__ import annotations

import pytest

from advisor.config import LLMProvider
from advisor.narrative.advisor import SECTION_ORDER, advisor
from advisor.narrative.errors import MissingAPIKeyError, ProviderNotImplementedError
from advisor.schema import Facts

from .conftest import RecordingClient, settings_for


def test_returns_three_sections(facts: Facts, recording_client: RecordingClient) -> None:
    result = advisor(facts, client=recording_client)
    assert result.executive_summary
    assert result.risk_commentary
    assert len(result.recommendations) == 3
    assert result.degraded is False
    assert result.provider == "mock"


def test_calls_client_once_per_section(facts: Facts, recording_client: RecordingClient) -> None:
    advisor(facts, client=recording_client)
    assert len(recording_client.calls) == len(SECTION_ORDER)


def test_client_receives_only_facts_context(
    facts: Facts, recording_client: RecordingClient
) -> None:
    advisor(facts, client=recording_client)
    prompt0 = recording_client.calls[0][0]
    assert "2200" in prompt0  # a real KPI figure from Facts
    for prompt, _system in recording_client.calls:
        assert "raw_label" not in prompt
        assert "source_ref" not in prompt


def test_rejects_non_facts(recording_client: RecordingClient) -> None:
    with pytest.raises(TypeError):
        advisor("not facts", client=recording_client)  # type: ignore[arg-type]


def test_recommendations_split(facts: Facts) -> None:
    client = RecordingClient(responses=["E", "R", "```\n- a\n* b\n1. c\n\n```"])
    result = advisor(facts, client=client)
    assert result.recommendations == ["a", "b", "c"]


def test_fail_soft_missing_key_degrades(facts: Facts) -> None:
    result = advisor(
        facts, settings=settings_for(LLMProvider.gemini, with_key=False), fail_soft=True
    )
    assert result.degraded is True
    assert result.provider == "none"


def test_fail_hard_missing_key_raises(facts: Facts) -> None:
    with pytest.raises(MissingAPIKeyError):
        advisor(facts, settings=settings_for(LLMProvider.gemini, with_key=False), fail_soft=False)


def test_stub_not_implemented_mapped(facts: Facts) -> None:
    settings = settings_for(LLMProvider.openai, with_key=True)
    with pytest.raises(ProviderNotImplementedError):
        advisor(facts, settings=settings, fail_soft=False)
    assert advisor(facts, settings=settings, fail_soft=True).degraded is True


def test_empty_response_handling(facts: Facts) -> None:
    class EmptyClient:
        provider = "mock"
        model = "m"

        def generate(self, prompt: str, *, system: str | None = None) -> str:
            return "   "

    assert advisor(facts, client=EmptyClient(), fail_soft=True).degraded is True


def test_facts_not_mutated(facts: Facts, recording_client: RecordingClient) -> None:
    snapshot = facts.model_dump(mode="json")
    advisor(facts, client=recording_client)
    assert facts.model_dump(mode="json") == snapshot
