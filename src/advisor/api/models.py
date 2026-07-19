"""Pydantic request/response DTOs for the HTTP boundary."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from advisor.narrative.advisor import Advisory
from advisor.schema import (
    AssumptionDelta,
    DeltaOp,
    DeltaTarget,
    Facts,
    IncomeStatement,
    PeriodType,
    Scenario,
    ScenarioComparison,
)


class ExportFormat(StrEnum):
    EXCEL = "excel"
    PDF = "pdf"
    WORD = "word"
    DASHBOARD = "dashboard"


class PeriodSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    period_type: PeriodType
    fiscal_year: int
    sequence: int


class StatementSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_name: str
    currency: str
    volume_unit: str
    n_periods: int
    periods: list[PeriodSummary]
    source_file: str | None = None


class UploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    summary: StatementSummary
    warnings: list[str] = []


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    include_narrative: bool = True


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    facts: Facts
    narrative: Advisory | None
    dashboard: dict[str, Any]


class ScenarioAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revenue_pct: Decimal | None = None
    cogs_pct: Decimal | None = None
    price_per_mt_pct: Decimal | None = None
    volume_pct: Decimal | None = None
    opex_pct: Decimal | None = None
    finance_cost_pct: Decimal | None = None
    period_label: str | None = None


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    name: str = "What-if"
    assumptions: ScenarioAssumptions
    include_narrative: bool = False


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    scenario_facts: Facts
    comparison: ScenarioComparison
    dashboard: dict[str, Any]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    reply: str
    history: list[ChatMessage]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"]
    version: str
    provider: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    detail: str


def to_statement_summary(stmt: IncomeStatement) -> StatementSummary:
    return StatementSummary(
        company_name=stmt.entity.company_name,
        currency=stmt.entity.currency,
        volume_unit=stmt.entity.volume_unit,
        n_periods=len(stmt.periods),
        periods=[
            PeriodSummary(
                label=p.meta.label,
                period_type=p.meta.period_type,
                fiscal_year=p.meta.fiscal_year,
                sequence=p.meta.sequence,
            )
            for p in stmt.periods
        ],
        source_file=stmt.source.source_file if stmt.source else None,
    )


_PCT_TARGETS: tuple[tuple[str, DeltaTarget], ...] = (
    ("revenue_pct", DeltaTarget.REVENUE),
    ("cogs_pct", DeltaTarget.COGS),
    ("price_per_mt_pct", DeltaTarget.PRICE_PER_MT),
    ("volume_pct", DeltaTarget.VOLUME),
    ("finance_cost_pct", DeltaTarget.FINANCE_COST),
)
_OPEX_TARGETS: tuple[DeltaTarget, ...] = (
    DeltaTarget.OPEX_ADMINISTRATIVE,
    DeltaTarget.OPEX_SELLING_DISTRIBUTION,
    DeltaTarget.OPEX_OTHER,
)


def to_scenario_model(name: str, assumptions: ScenarioAssumptions) -> Scenario:
    """Map flat percentage assumptions onto the engine Scenario model."""
    deltas: list[AssumptionDelta] = []
    applies_to = assumptions.period_label
    for attr, target in _PCT_TARGETS:
        magnitude = getattr(assumptions, attr)
        if magnitude is not None:
            deltas.append(
                AssumptionDelta(
                    target=target, op=DeltaOp.PCT, magnitude=magnitude, applies_to=applies_to
                )
            )
    if assumptions.opex_pct is not None:
        for target in _OPEX_TARGETS:
            deltas.append(
                AssumptionDelta(
                    target=target,
                    op=DeltaOp.PCT,
                    magnitude=assumptions.opex_pct,
                    applies_to=applies_to,
                )
            )
    return Scenario(name=name, deltas=deltas)
