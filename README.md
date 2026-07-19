# Master of Coin AI

> *The engine counts the coins. The AI tells the story.*

**Master of Coin AI** is a standalone Windows desktop AI financial advisor for **any
company**. Point it at your income statement (.xlsx) and it computes the
financials **deterministically**, has an LLM write the executive advisory layer
on top, and produces an enhanced Excel workbook, a PDF board note, a Word memo,
and an interactive dashboard — plus conversational and what-if modes.

> **Trust model:** the engine computes every number (reproducible, auditable).
> The LLM only writes *about* those numbers — it never invents or computes a figure.

Company name, currency, volume unit, and fiscal year end are all configurable —
nothing about your company is baked into the code.

## Getting your data in

Download the **blank Excel template** from the app (the *Excel template* button
next to Upload, or `GET /api/template`), or use
[`examples/income_statement_template.xlsx`](examples/income_statement_template.xlsx).

The template shows exactly where the data goes:

- One reporting period per **column** — headers like `FY2024`, `FY2023-24`,
  `Q1 FY2024`, `H1 FY2024`, `Jan 2024` are all recognised.
- One line item per **row**, label in column A. Only **Revenue** and **Cost of
  Goods Sold** are required; everything else (gross profit, opex breakdown,
  finance cost, tax, net profit, sales volume) is optional.
- Common label variants are recognised (`Turnover`, `Cost of Sales`, `PAT`, …) —
  the full alias list is on the template's *Instructions* sheet.
- Figures reported "in '000" (or lakh/crore/million) are detected from the
  header and scaled automatically. Unrecognised rows are preserved, not discarded.

## Development setup

Requires **Python 3.11+**.

```powershell
# from the project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # PowerShell  (use .venv\Scripts\activate.bat in cmd)
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

On macOS/Linux the venv activation is `source .venv/bin/activate`.

### Configuration

Copy `.env.example` to `.env`. Two things live there:

**LLM provider** (optional — the app runs offline in degraded mode without one):

```
LLM_PROVIDER=gemini        # gemini | openai | anthropic | ollama
GEMINI_API_KEY=your_key_here
```

**Company profile** (optional — brands the reports, prompts, and dashboard):

```
COMPANY_NAME=Acme Manufacturing Ltd.
GROUP_NAME=                # parent group, if any
CURRENCY=USD
VOLUME_UNIT=MT
FISCAL_YEAR_END_MONTH=12   # 12 = calendar year; 6 = July–June fiscal year
```

Editable KPI thresholds live in `config/thresholds.yaml` (user data, never hard-coded).

## Running the checks

A single command runs formatting, lint, strict type-checking, tests, and the
coverage gates (≥90% overall, **100% on `engine/`**):

```powershell
python scripts/check.py
```

Or run the tests alone:

```powershell
pytest
```

## Running the desktop app

```powershell
master-of-coin           # launches the FastAPI server + native pywebview window
```

## Building the Windows .exe

```powershell
pip install -e ".[package]"
python packaging/build.py                        # -> packaging/dist/Master of Coin AI.exe
& "packaging\dist\Master of Coin AI.exe" --selfcheck   # headless sanity check
```

The spec bundles the engine, FastAPI, the static `web/` dashboard, and
`config/thresholds.yaml`. The `.exe` needs only a `.env` (for the LLM key and
company profile) on a clean machine; it runs fully offline in degraded mode
without one.

## Project layout

```
src/advisor/
  config.py            # settings (pydantic-settings) + thresholds loader
  schema.py            # canonical pydantic models + frozen Facts
  ingestion/           # read & extract income statement -> canonical schema
  engine/              # PURE deterministic: kpis, variance, anomaly, scenario
  narrative/           # provider-agnostic LLM adapter + prompt templates
  reports/             # excel, word, pdf, dashboard, input-template generators
  api/                 # FastAPI app + routes
  app.py               # pywebview launcher
web/                   # static dashboard (+ vendored chart.js)
config/thresholds.yaml
examples/              # blank income-statement input template
tests/{unit,integration,e2e}
packaging/             # pyinstaller spec + build script
```

## How it was built

Milestone by milestone (engine-first), with strict TDD throughout: **M0**
scaffolding → M1 schema & ingestion → M2 deterministic engine → M3
scenario/what-if → M4 narrative → M5 reports → M6 API → M7 desktop UI →
M8 packaged `.exe`. Quality gates on every change: pytest (≥90% coverage
overall, 100% on the engine), ruff, and mypy `--strict`.

## License

[MIT](LICENSE)
