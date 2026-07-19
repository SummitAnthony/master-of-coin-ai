"""Tests for loading the user-editable thresholds YAML."""

from __future__ import annotations

from pathlib import Path

import pytest

from advisor.config import ConfigError, load_thresholds


def test_loads_bundled_thresholds() -> None:
    data = load_thresholds()
    assert "margins" in data
    assert data["margins"]["gross_margin_pct"]["green"] == 18.0
    assert data["margins"]["gross_margin_pct"]["direction"] == "higher_is_better"


def test_load_thresholds_explicit_path(tmp_path: Path) -> None:
    p = tmp_path / "t.yaml"
    p.write_text("margins:\n  x: 1\n", encoding="utf-8")
    assert load_thresholds(p) == {"margins": {"x": 1}}


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_thresholds(tmp_path / "nope.yaml")


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("margins: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_thresholds(p)


def test_non_mapping_raises(tmp_path: Path) -> None:
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        load_thresholds(p)
