"""Branded PDF board note (ReportLab Platypus), with deterministic bytes."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from advisor import PRODUCT_NAME
from advisor.narrative.advisor import Advisory
from advisor.schema import Facts

from .formatting import BRAND_PRIMARY_HEX, DISCLAIMER, format_pct, status_hex

# Deterministic output: fixed metadata + uncompressed (greppable) content streams.
rl_config.invariant = 1
rl_config.pageCompression = 0

_STYLES = getSampleStyleSheet()


def _para(text: str, style: str = "BodyText") -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), _STYLES[style])


def _scorecard_table(facts: Facts) -> Table:
    latest = facts.latest_period.label
    rows: list[list[Any]] = [["KPI", "Value", "Status"]]
    style_cmds: list[tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{BRAND_PRIMARY_HEX}")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]
    for i, s in enumerate((s for s in facts.statuses if s.period == latest), start=1):
        value = format_pct(s.value) if s.value is not None else "n/a"
        rows.append([s.metric, value, s.status.value])
        style_cmds.append(
            ("TEXTCOLOR", (2, i), (2, i), colors.HexColor(f"#{status_hex(s.status)}"))
        )
    table = Table(rows, hAlign="LEFT")
    table.setStyle(TableStyle(style_cmds))
    return table


def build_story(facts: Facts, narrative: Advisory, *, generated_at: datetime) -> list[Any]:
    entity = facts.entity
    title = (
        f"{entity.group_name} — {entity.company_name}" if entity.group_name else entity.company_name
    )
    story: list[Any] = [
        _para(title, "Title"),
        _para(f"{PRODUCT_NAME} — Board Note", "Heading2"),
        _para(f"Generated: {generated_at.isoformat()}"),
        _para(f"Latest period: {facts.latest_period.label}"),
        Spacer(1, 12),
        _para("Executive Summary", "Heading1"),
        _para(narrative.executive_summary),
        Spacer(1, 12),
        _para("KPI Scorecard (latest period)", "Heading1"),
        _scorecard_table(facts),
        Spacer(1, 12),
        _para("Risk Commentary", "Heading1"),
        _para(narrative.risk_commentary),
        _para("Recommendations", "Heading1"),
    ]
    for rec in narrative.recommendations:
        story.append(_para(f"• {rec}"))
    if facts.anomalies:
        story.append(_para("Anomalies", "Heading1"))
        for a in facts.anomalies:
            story.append(_para(f"[{a.severity.value}] {a.code} — {a.period} ({a.metric})"))
    story.append(Spacer(1, 18))
    story.append(_para(DISCLAIMER, "Italic"))
    return story


def build_pdf_bytes(facts: Facts, narrative: Advisory, *, generated_at: datetime) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"{PRODUCT_NAME} — Board Note")
    doc.build(build_story(facts, narrative, generated_at=generated_at))
    return buffer.getvalue()


def write_pdf(facts: Facts, narrative: Advisory, path: Path, *, generated_at: datetime) -> Path:
    path.write_bytes(build_pdf_bytes(facts, narrative, generated_at=generated_at))
    return path
