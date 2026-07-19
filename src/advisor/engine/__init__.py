"""Deterministic analytics engine (PURE).

No network access and no LLM imports. Pure functions over canonical models
that produce the frozen ``Facts`` object. Enforced by an architecture test.
"""

from __future__ import annotations

from .facts import ENGINE_VERSION, build_facts
from .kpis import compute_period_kpis, kpi_value
from .scenario import ScenarioError, apply_scenario, compare_facts, run_scenario

__all__ = [
    "ENGINE_VERSION",
    "ScenarioError",
    "apply_scenario",
    "build_facts",
    "compare_facts",
    "compute_period_kpis",
    "kpi_value",
    "run_scenario",
]
