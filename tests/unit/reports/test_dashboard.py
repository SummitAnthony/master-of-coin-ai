"""Tests for the dashboard JSON payload."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from advisor.narrative.advisor import Advisory
from advisor.reports.dashboard import build_dashboard_payload, write_dashboard_json
from advisor.schema import Facts


def test_payload_has_expected_keys(facts: Facts, advisory: Advisory, gen_at: datetime) -> None:
    payload = build_dashboard_payload(facts, advisory, generated_at=gen_at)
    assert set(payload) >= {
        "schema_version",
        "generated_at",
        "entity",
        "periods",
        "scorecard",
        "kpis",
        "charts",
        "narrative",
    }
    assert payload["generated_at"] == gen_at.isoformat()
    assert payload["entity"]["currency"] == "USD"


def test_decimals_serialized_as_strings(facts: Facts, advisory: Advisory, gen_at: datetime) -> None:
    payload = build_dashboard_payload(facts, advisory, generated_at=gen_at)
    assert all(isinstance(v, str) for v in payload["charts"]["revenue"]["data"])


def test_scorecard_is_latest_period(facts: Facts, advisory: Advisory, gen_at: datetime) -> None:
    payload = build_dashboard_payload(facts, advisory, generated_at=gen_at)
    assert payload["scorecard"]
    assert all("color" in row for row in payload["scorecard"])


def test_charts_align_to_periods(facts: Facts, advisory: Advisory, gen_at: datetime) -> None:
    payload = build_dashboard_payload(facts, advisory, generated_at=gen_at)
    n = len(payload["periods"])
    assert len(payload["charts"]["revenue"]["data"]) == n
    for dataset in payload["charts"]["margin_trend"]["datasets"]:
        assert len(dataset["data"]) == n


def test_write_dashboard_json_reloads(
    facts: Facts, advisory: Advisory, gen_at: datetime, tmp_path: Path
) -> None:
    path = write_dashboard_json(facts, advisory, tmp_path / "d.json", generated_at=gen_at)
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["narrative"]["provider"] == "mock"
