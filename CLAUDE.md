# CLAUDE.md — Master of Coin AI

Project rules and memory for Claude Code. Read this before every change. Keep these rules in force for the whole build.

## What this is

Master of Coin AI is a standalone Windows desktop AI financial advisor for any company. It reads an income statement, computes financials deterministically, has an LLM write the executive advisory layer, and produces an enhanced Excel workbook, a PDF board note, a Word memo, and an interactive dashboard — plus conversational and what-if modes. Company name, currency, volume unit, and fiscal year end are configurable via `.env` (company profile in `Settings` / `EntityMeta`); neutral defaults are "Your Company" / USD / MT / calendar year. The project is public/open-source: never hardcode a specific company, currency, or fiscal calendar into code.

## Hard rules (do not violate)

1. **TDD, strictly, everywhere.** Write the failing test first (red) → minimum code to pass (green) → refactor. No production code exists without a test that drove it. Never leave the tree red. Show the failing test before the implementation.
2. **Hybrid trust model.** All figures come from the deterministic engine and are reproducible. The **LLM never invents or computes numbers** — it receives only a frozen `Facts` object and writes prose about it. The narrative layer must not be able to import or read raw inputs; add a test that asserts this.
3. **Pure engine.** `engine/` and `ingestion/` have **no network and no LLM imports** — pure functions over data, offline-runnable. Add a test asserting these packages don't import narrative/network libs.
4. **Secrets via env only.** Keys come from `.env` (gitignored). Never hardcode, log, or print keys. Maintain `.env.example`.
5. **Provider-agnostic LLM.** One `LLMClient` interface; backends Gemini / OpenAI / Anthropic / Ollama selected by `LLM_PROVIDER`. Default Gemini (free tier). **LLM is always mocked in tests** — tests are deterministic and offline.
6. **Thresholds are user data.** Live in `config/thresholds.yaml`, never baked into code.

## Stack

Python 3.11+ · FastAPI · vanilla HTML/CSS/JS + Chart.js (vendored, offline) · pywebview (native window) · openpyxl (Excel) · python-docx (Word) · ReportLab (PDF) · pydantic v2 · pydantic-settings · pytest/pytest-cov/pytest-mock · ruff + mypy (strict). Package to a single Windows `.exe` with PyInstaller.

## Quality gates (must pass before any milestone is "done")

- `pytest` green; coverage **≥90% overall** and **100% on `engine/`**.
- `ruff` clean (lint + format); `mypy --strict` clean.
- A single `make check` (or `scripts/check`) runs ruff, mypy, and pytest+coverage.

## Layout

```
src/advisor/{schema.py, ingestion/, engine/, narrative/, reports/, api/, app.py}
web/                # static dashboard + vendored chart.js
config/thresholds.yaml
tests/{unit,integration,e2e,fixtures}
packaging/          # pyinstaller spec + build script
```

## Build order (engine-first — finish each before the next)

M0 scaffolding/tooling → M1 schema & ingestion → M2 deterministic engine (KPIs, variance, anomaly) → M3 scenario/what-if → M4 narrative adapter → M5 report generators (Excel/PDF/Word/dashboard) → M6 FastAPI API → M7 pywebview UI → M8 PyInstaller `.exe`.

At each milestone, stop and report: what was built, test/coverage status, next milestone.

## Conventions

- Small, per-milestone commits with clear messages.
- Keep `README.md` current: dev run, tests, `.exe` build, required `.env` keys.
- Test fixtures are **synthetic** workbooks built in-test with openpyxl — never commit real company financial data.
- Format monetary output with the configured currency; volumes with the configured unit (`EntityMeta`).
- The blank input template lives in `reports/template.py` and must always round-trip through `extract_income_statement` (guarded by test).
