#!/usr/bin/env python
"""Run all quality gates in order; exit non-zero on the first failure.

  1. ruff format --check   (formatting)
  2. ruff check            (lint)
  3. mypy                  (strict type-checking)
  4. pytest                (tests + >=90% overall coverage gate, from pyproject)
  5. coverage report       (engine package must be 100%)

Run with the project's virtualenv Python:  python scripts/check.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Resolve tools from the same environment as the interpreter running this script,
# so it works whether or not the venv is "activated".
BIN = Path(sys.executable).parent
ROOT = Path(__file__).resolve().parent.parent


def _tool(name: str) -> str:
    """Resolve a console-script name to the venv executable (Windows-safe)."""
    if os.name == "nt":
        exe = BIN / f"{name}.exe"
        if exe.exists():
            return str(exe)
    candidate = BIN / name
    return str(candidate) if candidate.exists() else name


def run(cmd: list[str]) -> int:
    print(f"\n=== {' '.join(cmd)} ===", flush=True)
    env = os.environ.copy()
    env["PATH"] = str(BIN) + os.pathsep + env.get("PATH", "")
    resolved = [_tool(cmd[0]), *cmd[1:]]
    return subprocess.call(resolved, cwd=ROOT, env=env)


def main() -> int:
    steps: list[list[str]] = [
        ["ruff", "format", "--check", "."],
        ["ruff", "check", "."],
        ["mypy"],
        ["pytest"],
        # Enforce 100% coverage on the pure engine package (reuses pytest's .coverage).
        ["coverage", "report", "--include=*/advisor/engine/*", "--fail-under=100"],
    ]
    for cmd in steps:
        code = run(cmd)
        if code != 0:
            print(f"\nFAILED: {' '.join(cmd)}  (exit {code})")
            return code
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
