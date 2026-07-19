"""Architecture guards.

The pure layers (``engine`` and ``ingestion``) must not import network or LLM
libraries, nor the narrative/API layers. This protects the hybrid trust model:
all figures come from deterministic, offline code.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

import advisor

PKG_ROOT = Path(advisor.__file__).resolve().parent

FORBIDDEN_PREFIXES: tuple[str, ...] = (
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request",
    "urllib3",
    "socket",
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "fastapi",
    "uvicorn",
    "starlette",
    "advisor.narrative",
    "advisor.api",
)


def _imported_modules(py: Path) -> list[str]:
    tree = ast.parse(py.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return names


@pytest.mark.parametrize("pkg", ["engine", "ingestion"])
def test_pure_layers_have_no_network_or_llm_imports(pkg: str) -> None:
    offenders: list[str] = []
    for py in sorted((PKG_ROOT / pkg).rglob("*.py")):
        for mod in _imported_modules(py):
            if mod.startswith(FORBIDDEN_PREFIXES):
                offenders.append(f"{py.name}: {mod}")
    assert not offenders, f"Pure layer '{pkg}' has forbidden imports: {offenders}"


def test_pure_packages_import_cleanly() -> None:
    # Importing them also ensures they are measured for coverage.
    for name in ("advisor.engine", "advisor.ingestion"):
        importlib.import_module(name)


def test_openpyxl_confined_to_workbook() -> None:
    ingestion = PKG_ROOT / "ingestion"
    for py in sorted(ingestion.rglob("*.py")):
        imports = _imported_modules(py)
        uses_openpyxl = any(m == "openpyxl" or m.startswith("openpyxl.") for m in imports)
        if uses_openpyxl:
            assert py.name == "workbook.py", f"openpyxl imported outside workbook.py: {py.name}"
