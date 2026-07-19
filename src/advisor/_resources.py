"""Resolve bundled data files in both dev and PyInstaller-frozen runs."""

from __future__ import annotations

import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):  # running inside a PyInstaller bundle
        meipass = getattr(sys, "_MEIPASS", None)
        return Path(meipass) if meipass else Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]  # project root in a source checkout


def resource_path(relative: str) -> Path:
    """Path to a bundled resource (e.g. 'web' or 'config/thresholds.yaml')."""
    return _base_dir() / relative
