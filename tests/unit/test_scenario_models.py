"""Tests for the scenario input/output models."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from advisor.schema import AssumptionDelta, DeltaOp, DeltaTarget, Scenario


def test_assumption_delta_json_roundtrip() -> None:
    d = AssumptionDelta(target=DeltaTarget.COGS, op=DeltaOp.PCT, magnitude=Decimal("8"))
    assert d.model_dump(mode="json") == {
        "target": "cogs",
        "op": "pct",
        "magnitude": "8",
        "applies_to": None,
    }


def test_delta_op_and_target_are_str_enums() -> None:
    assert DeltaOp.PCT.value == "pct"
    assert DeltaTarget.PRICE_PER_MT.value == "price_per_mt"


def test_delta_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        AssumptionDelta(target=DeltaTarget.COGS, op=DeltaOp.PCT, magnitude=Decimal("8"), x=1)  # type: ignore[call-arg]


def test_delta_is_frozen() -> None:
    d = AssumptionDelta(target=DeltaTarget.COGS, op=DeltaOp.PCT, magnitude=Decimal("8"))
    with pytest.raises(ValidationError):
        d.magnitude = Decimal("9")


def test_invalid_target_value_rejected() -> None:
    with pytest.raises(ValidationError):
        AssumptionDelta(target="bogus", op=DeltaOp.PCT, magnitude=Decimal("1"))  # type: ignore[arg-type]


def test_magnitude_accepts_decimal_string() -> None:
    d = AssumptionDelta(target=DeltaTarget.COGS, op=DeltaOp.PCT, magnitude="8.5")  # type: ignore[arg-type]
    assert d.magnitude == Decimal("8.5")


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
def test_magnitude_rejects_nan_inf(bad: Decimal) -> None:
    with pytest.raises(ValidationError):
        AssumptionDelta(target=DeltaTarget.COGS, op=DeltaOp.PCT, magnitude=bad)


def test_scenario_requires_nonempty_name() -> None:
    with pytest.raises(ValidationError):
        Scenario(name="   ")


def test_scenario_defaults_empty_deltas() -> None:
    assert Scenario(name="base").deltas == []
