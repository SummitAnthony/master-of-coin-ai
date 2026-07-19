"""Guard: the narrative layer must not import ingestion or raw containers."""

from __future__ import annotations

import ast
from pathlib import Path

import advisor

NARRATIVE = Path(advisor.__file__).resolve().parent / "narrative"


def _imports(py: Path) -> list[str]:
    tree = ast.parse(py.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_narrative_does_not_import_ingestion() -> None:
    for py in sorted(NARRATIVE.rglob("*.py")):
        for module in _imports(py):
            assert "advisor.ingestion" not in module, f"{py.name} imports {module}"
