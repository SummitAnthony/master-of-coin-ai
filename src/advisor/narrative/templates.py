"""Prompt templates for the advisory sections.

Defaults are inlined as constants so they always resolve inside a PyInstaller
bundle (no data-file lookup). An optional YAML override can be loaded from disk.
Rendering is plain ``{facts}`` substitution (no str.format), so stray braces in
the data never raise.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from .context import NarrativeContext

_SYSTEM = (
    "You are the executive financial advisor for {company}. You write concise, board-ready "
    "prose in British English. All figures are pre-computed by the deterministic analytics "
    "engine and given to you as JSON facts. NEVER invent, recompute, or alter any number; "
    "only describe and interpret the figures provided. Currency is {currency}; volumes are "
    "in {volume_unit}."
)
_EXECUTIVE_SUMMARY = (
    "Write a 3-5 sentence executive summary of {company}'s latest-period performance, citing only "
    "figures present in the facts (revenue, margins, net profit, volume). Lead with the headline "
    "result.\n\nFACTS:\n{facts}"
)
_RISK_COMMENTARY = (
    "Write a short risk commentary (3-5 sentences) grounded only in the provided statuses, "
    "variances, and anomalies. Name the specific KPIs that are amber/red and the anomalies that "
    "fired. Do not introduce figures not present in the facts.\n\nFACTS:\n{facts}"
)
_RECOMMENDATIONS = (
    "Provide 3-6 specific, actionable recommendations for {company} management as a plain "
    "bulleted list (one recommendation per line). Base each strictly on the provided "
    "facts.\n\nFACTS:\n{facts}"
)


class PromptTemplates(BaseModel):
    """The system prompt plus one instruction template per advisory section."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    system: str
    executive_summary: str
    risk_commentary: str
    recommendations: str


DEFAULT_TEMPLATES = PromptTemplates(
    system=_SYSTEM,
    executive_summary=_EXECUTIVE_SUMMARY,
    risk_commentary=_RISK_COMMENTARY,
    recommendations=_RECOMMENDATIONS,
)


def load_templates(path: Path | None = None) -> PromptTemplates:
    """Return the default templates, or load+validate a YAML override from disk."""
    if path is None:
        return DEFAULT_TEMPLATES
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not read templates file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Templates file {path} must contain a mapping")
    return PromptTemplates.model_validate(data)


def company_phrase(context: NarrativeContext) -> str:
    """The company's display name, with its group appended when one is set."""
    if context.group_name:
        return f"{context.company_name} ({context.group_name})"
    return context.company_name


def _substitute_profile(template: str, context: NarrativeContext) -> str:
    return (
        template.replace("\r\n", "\n")
        .replace("{company}", company_phrase(context))
        .replace("{currency}", context.currency)
        .replace("{volume_unit}", context.volume_unit)
    )


def render_system(template: str, context: NarrativeContext) -> str:
    """Resolve the company-profile placeholders in the system prompt."""
    return _substitute_profile(template, context)


def render(template: str, context: NarrativeContext) -> str:
    """Resolve profile placeholders, then inject the context's JSON {facts} block."""
    block = context.as_prompt_block()
    return _substitute_profile(template, context).replace("{facts}", block)
