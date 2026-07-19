#!/usr/bin/env python
"""Build the single-file Windows executable with PyInstaller.

Usage:  python packaging/build.py
Output: packaging/dist/"Master of Coin AI.exe"
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(PACKAGING / "dist"),
        "--workpath",
        str(PACKAGING / "build"),
        str(PACKAGING / "master_of_coin.spec"),
    ]
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
