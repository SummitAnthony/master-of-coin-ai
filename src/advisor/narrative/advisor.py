"""Narrative orchestrator: frozen Facts -> Advisory prose.

``advisor()`` accepts ONLY ``Facts`` (which carries no raw inputs), builds a
prompt-safe context, renders each section, calls the (mocked/real) client once
per section, and returns a frozen ``Advisory``. With ``fail_soft=True`` it
degrades to deterministic template-only prose instead of raising, so the demo
still produces output offline.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict

from advisor.config import Settings, load_settings
from advisor.schema import Facts

from .client import SupportsGenerate
from .context import NarrativeContext, build_context
from .errors import LLMResponseError, MissingAPIKeyError, ProviderNotImplementedError
from .factory import get_llm_client
from .templates import PromptTemplates, company_phrase, load_templates, render, render_system

SECTION_ORDER: Final[tuple[str, str, str]] = (
    "executive_summary",
    "risk_commentary",
    "recommendations",
)


class Advisory(BaseModel):
    """Frozen advisory output assembled from the LLM (or a degraded fallback)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    executive_summary: str
    risk_commentary: str
    recommendations: list[str]
    provider: str
    model: str
    degraded: bool = False


def _split_recommendations(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        cleaned = stripped.lstrip("-*•0123456789. ").strip()
        if cleaned:
            out.append(cleaned)
    return out or [text.strip()]


def _fallback_advisory(context: NarrativeContext) -> Advisory:
    summary = (
        f"Performance summary for {company_phrase(context)}, latest period "
        f"{context.latest_period}. All figures are computed deterministically by the engine; "
        f"AI narrative is unavailable in this run (offline / no provider configured)."
    )
    risk = (
        "Automated risk narrative is unavailable. Review the KPI scorecard, the red/amber status "
        "flags, and any flagged anomalies below for the period's key risk signals."
    )
    recommendations = [
        "Configure an LLM provider and API key to enable AI commentary.",
        "Review all amber/red KPI statuses for the latest period.",
        "Investigate every flagged anomaly and its numeric context.",
    ]
    return Advisory(
        executive_summary=summary,
        risk_commentary=risk,
        recommendations=recommendations,
        provider="none",
        model="none",
        degraded=True,
    )


def advisor(
    facts: Facts,
    templates: PromptTemplates | None = None,
    *,
    client: SupportsGenerate | None = None,
    settings: Settings | None = None,
    fail_soft: bool = True,
) -> Advisory:
    """Produce an :class:`Advisory` from ``facts``. The LLM only ever sees Facts."""
    if not isinstance(facts, Facts):
        raise TypeError("advisor() accepts only a Facts object")

    context = build_context(facts)
    templates = templates or load_templates()

    own_client = False
    if client is None:
        try:
            client = get_llm_client(settings or load_settings())
            own_client = True
        except MissingAPIKeyError:
            if fail_soft:
                return _fallback_advisory(context)
            raise

    assert client is not None  # resolved above, or we returned/raised

    try:
        sections: dict[str, str] = {}
        for section in SECTION_ORDER:
            text = client.generate(
                render(getattr(templates, section), context),
                system=render_system(templates.system, context),
            )
            if not text.strip():
                raise LLMResponseError(getattr(client, "provider", "?"), "empty completion")
            sections[section] = text.strip()
    except NotImplementedError as exc:
        if fail_soft:
            return _fallback_advisory(context)
        raise ProviderNotImplementedError(getattr(client, "provider", "?")) from exc
    except LLMResponseError:
        if fail_soft:
            return _fallback_advisory(context)
        raise
    finally:
        if own_client:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    return Advisory(
        executive_summary=sections["executive_summary"],
        risk_commentary=sections["risk_commentary"],
        recommendations=_split_recommendations(sections["recommendations"]),
        provider=client.provider,
        model=client.model,
        degraded=False,
    )
