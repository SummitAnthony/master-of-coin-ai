"""Canonical data models for Master of Coin AI.

This module is the single source of truth for the shared schema. In M1 it
defines the *income-statement side* of the contract: the string enums plus the
``IncomeStatement`` graph produced by ingestion and consumed by the engine.

``IncomeStatement`` is the ONLY object that holds raw figures; it is
deliberately never passed to the narrative layer. The Facts-graph models
(``PeriodKPIs``, ``Variance``, ``KpiStatus``, ``Anomaly``, ``Facts`` …) are
added in M2 alongside the engine that computes them.

All money is :class:`~decimal.Decimal` in the configured reporting currency;
volumes are Decimal in the configured volume unit.
No floats anywhere in the value path.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Final, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

# Structural tolerance for "as reported" subtotal vs derived checks. This is a
# rounding allowance (e.g. after scale multiplication), NOT a business threshold.
CONSISTENCY_TOL: Final[Decimal] = Decimal("1.00")


# --------------------------------------------------------------------------- #
# Shared string enums (lowercase values -> golden-file / dashboard JSON stable)
# --------------------------------------------------------------------------- #
class Status(StrEnum):
    """KPI traffic-light band."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"


class ThresholdDirection(StrEnum):
    """How a KPI value maps to a band."""

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class Direction(StrEnum):
    """Sign of a variance change."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class PeriodType(StrEnum):
    """Granularity of a reporting period."""

    MONTH = "month"
    QUARTER = "quarter"
    HALF = "half"
    YEAR = "year"


class PeriodKind(StrEnum):
    """Data provenance of a period."""

    ACTUAL = "actual"
    BUDGET = "budget"
    FORECAST = "forecast"


class VarianceBasis(StrEnum):
    """Comparison basis for period-over-period variance."""

    SEQUENTIAL = "sequential"
    MOM = "mom"
    QOQ = "qoq"
    YOY = "yoy"


class AnomalySeverity(StrEnum):
    """Weight of an anomaly finding."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# --------------------------------------------------------------------------- #
# Decimal validators / annotated money types
# --------------------------------------------------------------------------- #
def _finite(v: Decimal) -> Decimal:
    if not v.is_finite():
        raise ValueError("must be a finite number (no NaN/Infinity)")
    return v


def _non_negative(v: Decimal) -> Decimal:
    if v < 0:
        raise ValueError("must be non-negative")
    return v


def _positive(v: Decimal) -> Decimal:
    if v <= 0:
        raise ValueError("must be positive")
    return v


Money = Annotated[Decimal, AfterValidator(_finite)]
"""A finite Decimal amount; may be negative (e.g. a loss or contra line)."""

NonNegMoney = Annotated[Decimal, AfterValidator(_finite), AfterValidator(_non_negative)]
"""A finite, non-negative Decimal amount."""

PositiveDecimal = Annotated[Decimal, AfterValidator(_finite), AfterValidator(_positive)]
"""A finite, strictly-positive Decimal (e.g. a scale multiplier)."""


# --------------------------------------------------------------------------- #
# Income-statement graph
# --------------------------------------------------------------------------- #
class LineItem(BaseModel):
    """An atomic, traceable monetary line, with optional provenance."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1)
    amount: Money
    raw_label: str | None = None
    source_ref: str | None = None
    category: str | None = None


class PeriodMeta(BaseModel):
    """Metadata describing one income-statement column. Holds no figures."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    period_type: PeriodType
    fiscal_year: int = Field(ge=1900, le=2100)
    sequence: int = Field(ge=0)
    kind: PeriodKind = PeriodKind.ACTUAL
    sub_index: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    months: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if self.sub_index is not None:
            limits = {
                PeriodType.MONTH: 12,
                PeriodType.QUARTER: 4,
                PeriodType.HALF: 2,
                PeriodType.YEAR: 1,
            }
            upper = limits[self.period_type]
            if not 1 <= self.sub_index <= upper:
                raise ValueError(
                    f"sub_index {self.sub_index} out of range 1..{upper} "
                    f"for {self.period_type.value}"
                )
        return self


class OperatingExpenses(BaseModel):
    """Structured opex breakdown plus the detailed lines (preserved for reports)."""

    model_config = ConfigDict(extra="forbid")

    selling_distribution: NonNegMoney | None = None
    administrative: NonNegMoney | None = None
    other_opex: NonNegMoney | None = None
    total: NonNegMoney | None = None
    items: list[LineItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_total_consistency(self) -> Self:
        categories = (
            self.selling_distribution,
            self.administrative,
            self.other_opex,
        )
        if self.total is not None and all(c is not None for c in categories):
            component_sum = sum((c for c in categories if c is not None), Decimal(0))
            if abs(self.total - component_sum) > CONSISTENCY_TOL:
                raise ValueError("total is inconsistent with the sum of opex categories")
        return self


class Period(BaseModel):
    """One fully-mapped P&L column (as reported). Engine derivation happens in M2."""

    model_config = ConfigDict(extra="forbid")

    meta: PeriodMeta
    revenue: NonNegMoney
    cogs: NonNegMoney
    gross_profit: Money | None = None
    opex: OperatingExpenses = Field(default_factory=OperatingExpenses)
    operating_profit: Money | None = None
    other_income: Money | None = None
    finance_cost: NonNegMoney | None = None
    profit_before_tax: Money | None = None
    tax_expense: Money | None = None
    net_profit: Money | None = None
    volume_mt: NonNegMoney | None = None
    extra_lines: list[LineItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_gross_profit_consistency(self) -> Self:
        if self.gross_profit is not None:
            derived = self.revenue - self.cogs
            if abs(self.gross_profit - derived) > CONSISTENCY_TOL:
                raise ValueError("reported gross_profit is inconsistent with revenue - cogs")
        return self


class EntityMeta(BaseModel):
    """Company / reporting context (configurable per deployment).

    Frozen so the ``Facts`` graph (which embeds it) is fully immutable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    company_name: str = Field(default="Your Company", min_length=1)
    group_name: str = ""
    currency: str = Field(default="USD", min_length=1)
    volume_unit: str = Field(default="MT", min_length=1)
    fiscal_year_end_month: int = Field(default=12, ge=1, le=12)
    industry: str | None = None


class SourceMeta(BaseModel):
    """Ingestion provenance (audit only; never read by the engine's math)."""

    model_config = ConfigDict(extra="forbid")

    source_file: str | None = None
    sheet_name: str | None = None
    source_scale: PositiveDecimal = Decimal("1")
    extracted_with: str | None = None


class IncomeStatement(BaseModel):
    """Top-level canonical, validated, multi-period income statement."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    entity: EntityMeta = Field(default_factory=EntityMeta)
    periods: list[Period] = Field(min_length=1)
    source: SourceMeta | None = None

    @model_validator(mode="after")
    def _validate_and_sort_periods(self) -> Self:
        sequences = [p.meta.sequence for p in self.periods]
        labels = [p.meta.label for p in self.periods]
        if len(set(sequences)) != len(sequences):
            raise ValueError("period meta.sequence values must be unique")
        if len(set(labels)) != len(labels):
            raise ValueError("period meta.label values must be unique")
        self.periods.sort(key=lambda p: p.meta.sequence)
        return self


# --------------------------------------------------------------------------- #
# Facts graph (engine output). All frozen — consumed by the narrative layer,
# which receives ONLY Facts and never the raw IncomeStatement.
# --------------------------------------------------------------------------- #
class PeriodRef(BaseModel):
    """Lightweight period identity inside Facts (no raw figures)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    period_type: PeriodType
    fiscal_year: int
    sequence: int


class PeriodKPIs(BaseModel):
    """Engine-computed KPIs for one period: resolved figures, ratios, per-MT."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    period: PeriodRef
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    total_opex: Decimal
    operating_profit: Decimal
    other_income: Decimal
    finance_cost: Decimal
    profit_before_tax: Decimal
    tax_expense: Decimal
    net_profit: Decimal
    volume_mt: Decimal | None = None
    gross_margin_pct: Decimal | None = None
    operating_margin_pct: Decimal | None = None
    net_margin_pct: Decimal | None = None
    cogs_to_sales_pct: Decimal | None = None
    opex_to_sales_pct: Decimal | None = None
    finance_cost_to_sales_pct: Decimal | None = None
    selling_price_per_mt: Decimal | None = None
    cogs_per_mt: Decimal | None = None
    gross_profit_per_mt: Decimal | None = None
    expense_ratios_pct: dict[str, Decimal] = Field(default_factory=dict)


class Variance(BaseModel):
    """One metric's change between two periods on a given basis."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str
    basis: VarianceBasis
    from_period: str
    to_period: str
    from_value: Decimal | None
    to_value: Decimal | None
    absolute_change: Decimal | None
    pct_change: Decimal | None
    bps_change: Decimal | None
    direction: Direction


class KpiStatus(BaseModel):
    """Traffic-light evaluation of one KPI in one period vs thresholds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str
    period: str
    value: Decimal | None
    status: Status
    direction: ThresholdDirection
    green_at: Decimal
    yellow_at: Decimal
    message_code: str


class Anomaly(BaseModel):
    """A rule-fired finding: stable code + numeric context only, never prose."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    severity: AnomalySeverity
    period: str
    basis: VarianceBasis | None = None
    metric: str | None = None
    observed: Decimal | None = None
    threshold: Decimal | None = None
    context: dict[str, Decimal] = Field(default_factory=dict)
    message_code: str


class Facts(BaseModel):
    """The frozen, reproducible engine output handed to the narrative layer.

    Contains ONLY computed outputs — never an ``IncomeStatement``/``Period``/
    ``LineItem`` nor any raw provenance — so the LLM cannot read raw inputs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    engine_version: str
    entity: EntityMeta
    periods: list[PeriodRef]
    latest_period: PeriodRef
    kpis: list[PeriodKPIs]
    variances: list[Variance]
    statuses: list[KpiStatus]
    anomalies: list[Anomaly]


# --------------------------------------------------------------------------- #
# Scenario / what-if models (M3).
# --------------------------------------------------------------------------- #
class DeltaOp(StrEnum):
    """How an assumption delta changes a value."""

    PCT = "pct"  # value * (1 + magnitude/100)
    ABSOLUTE = "absolute"  # value + magnitude
    SET = "set"  # value := magnitude


class DeltaTarget(StrEnum):
    """Which canonical driver an assumption delta acts on."""

    REVENUE = "revenue"
    COGS = "cogs"
    PRICE_PER_MT = "price_per_mt"
    VOLUME = "volume"
    OPEX_ADMINISTRATIVE = "opex_administrative"
    OPEX_SELLING_DISTRIBUTION = "opex_selling_distribution"
    OPEX_OTHER = "opex_other"
    OTHER_INCOME = "other_income"
    FINANCE_COST = "finance_cost"
    TAX_EXPENSE = "tax_expense"


class AssumptionDelta(BaseModel):
    """One what-if assumption applied to a target driver."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target: DeltaTarget
    op: DeltaOp
    magnitude: Money
    applies_to: str | None = None  # period meta.label; None = all periods


class Scenario(BaseModel):
    """A named set of assumption deltas to apply to a base statement."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    description: str | None = None
    deltas: list[AssumptionDelta] = Field(default_factory=list)


class MetricDelta(BaseModel):
    """Base-vs-scenario change for one KPI in one period."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str
    period: str
    base_value: Decimal | None
    scenario_value: Decimal | None
    absolute_change: Decimal | None
    pct_change: Decimal | None
    direction: Direction


class ScenarioComparison(BaseModel):
    """All per-period, per-KPI deltas between base and scenario Facts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_name: str
    metric_deltas: list[MetricDelta]


class ScenarioResult(BaseModel):
    """A scenario run: the inputs, both Facts, and their comparison."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario: Scenario
    base_facts: Facts
    scenario_facts: Facts
    comparison: ScenarioComparison
