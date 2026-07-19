"""Smoke test for the packaged .exe (skipped until it is built)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

_EXE = Path(__file__).resolve().parents[2] / "packaging" / "dist" / "Master of Coin AI.exe"
_SENTINEL = Path(tempfile.gettempdir()) / "master_of_coin_selfcheck.txt"


def test_packaged_binary_selfcheck() -> None:
    if not _EXE.exists():
        pytest.skip("packaged binary not built (run python packaging/build.py)")
    _SENTINEL.unlink(missing_ok=True)
    result = subprocess.run([str(_EXE), "--selfcheck"], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    # Windowed (console=False) builds have no stdout, so the sentinel file is the
    # reliable channel; console builds also print to stdout.
    sentinel_text = _SENTINEL.read_text(encoding="utf-8") if _SENTINEL.exists() else ""
    assert "SELFCHECK OK" in (result.stdout + sentinel_text)
