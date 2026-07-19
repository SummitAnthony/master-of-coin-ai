# Master of Coin AI — Product & Capability Spec

> **Master of Coin AI** — a standalone Windows desktop AI financial advisor, currently
> configurable for **any company** via the `.env` company profile.
> Currency, volume unit, and fiscal calendar are all set in the `.env` company profile.

---

## 1. What it is

Master of Coin AI reads an income statement, computes the financials
**deterministically**, has a large language model write the executive advisory
layer on top, and produces a full set of board-ready deliverables — an enhanced
Excel workbook, a PDF board note, a Word memo, and an interactive dashboard —
plus conversational ("ask the data") and what-if ("scenario") modes.

It ships as a **single double-clickable Windows `.exe`**. No Python, no install,
no internet connection required. It runs fully offline in a degraded
(template-only) mode, and lights up the AI narrative when an LLM key is present.

---

## 2. The core idea — the hybrid trust model

This is the product's defining design decision and its main selling point to a
finance audience.

| Layer | Responsibility | Constraint |
| --- | --- | --- |
| **Deterministic engine** | Computes *every* figure — KPIs, ratios, variances, anomalies, scenarios | Pure functions over data. No network, no LLM, no floats (Decimal only). Reproducible and auditable. |
| **AI narrative layer** | Writes the *words* — summaries, risk commentary, recommendations, chat answers | Receives only a frozen `Facts` object. It **never sees raw inputs and never does arithmetic.** It writes *about* numbers it is handed. |

**Why it matters:** a generic AI asked to "analyze financials" will hallucinate
numbers, and one invented figure destroys trust with a board. Here the math and
the language are architecturally separated and can never blur.

This separation is **enforced by tests**, not just convention:
- `engine/` and `ingestion/` are asserted to import no network/LLM libraries.
- The narrative layer is asserted to receive only `Facts`, never the raw
  `IncomeStatement` that holds the original figures.

---

## 3. End-to-end pipeline

```
Excel income statement
        │
        ▼
[ Ingestion ]  read workbook → parse numbers → detect scale → map labels →
               detect periods → canonical, validated IncomeStatement
        │
        ▼
[ Engine ]     KPIs · variance · anomalies · status bands → frozen Facts graph
        │
        ├────────────────────────────► [ Scenario engine ]  what-if deltas → base-vs-scenario
        │
        ▼
[ Narrative ]  Facts → Advisory (executive summary, risk, recommendations)
               + Executive Committee personas + conversational chat
        │
        ▼
[ Reports ]    Excel workbook · PDF board note · Word memo · dashboard JSON
        │
        ▼
[ Desktop UI ] FastAPI + pywebview native window, glassy dashboard
```

---

## 4. Capability catalogue

### 4.1 Ingestion (`src/advisor/ingestion/`)
Turns a messy real-world spreadsheet into a clean, validated, canonical model.

- **Workbook reader** — opens the Excel file and locates the income-statement grid.
- **Number parsing** — robust parsing of human-entered numbers (parentheses for
  negatives, thousands separators, blanks).
- **Scale detection** — recognizes when figures are reported in thousands / lakh /
  crore and normalizes everything to absolute amounts.
- **Label mapping** — maps inconsistent real-world line labels (e.g. "Cost of
  Goods Sold", "COGS", "Cost of sales") onto a canonical schema, preserving the
  original raw label for audit.
- **Period detection** — recognizes the granularity (month / quarter / half /
  year) and provenance (actual / budget / forecast) of each column.
- **Extractor** — orchestrates the above into a validated `IncomeStatement`.
- **Structured errors** — typed ingestion errors for malformed input.

### 4.2 Deterministic engine (`src/advisor/engine/`) — 100% test coverage
Pure functions; no I/O, no network, no LLM. All money/volume are `Decimal`.

**KPIs (`kpis.py`)** — per period:
- Resolved subtotals: revenue, COGS, gross profit, total opex, operating profit,
  other income, finance cost, profit before tax, tax, net profit, volume (MT).
- Ratios: gross margin %, operating margin %, net margin %, COGS-to-sales %,
  opex-to-sales %, finance-cost-to-sales %.
- **Per-MT economics:** selling price per MT, COGS per MT, gross profit per MT.

**Variance (`variance.py`)** — period-over-period change on every metric, with
basis support (sequential / month-over-month / quarter-over-quarter /
year-over-year) and direction (up / down / flat).

**Anomaly detection (`anomaly.py`)** — rule-based, emitting stable codes,
severity (info / warning / critical), and the exact numeric context behind each
flag. Rules are driven by `config/thresholds.yaml`:
- Margin drop beyond a basis-point threshold vs the prior period.
- COGS growth outpacing sales growth beyond a percentage-point gap.
- Any cost line spiking beyond a percentage threshold.

**Status bands (`status.py`)** — traffic-light scoring (green / yellow / red /
unknown) of each KPI against the editable thresholds, honoring "higher is
better" vs "lower is better" direction.

**Facts builder (`facts.py`)** — assembles the immutable `Facts` graph (periods,
KPIs, variances, statuses, anomalies) that is the single hand-off to the AI.

**Rounding (`rounding.py`)** — centralized Decimal quantization for money,
percentages, and per-MT values, so every output is consistent.

### 4.3 Scenario / what-if engine (`src/advisor/engine/scenario.py`)
Pure and deterministic. The base statement is never mutated.

- **Assumption deltas** with three operations: percentage change, absolute
  change, or set-to-value.
- **Targets:** revenue, COGS, finance cost, other income, tax, operating-expense
  sub-lines (administrative / selling-distribution / other), **price per MT**,
  and **volume**.
- Re-runs the full Facts build on the transformed statement.
- Produces a structured **base-vs-scenario comparison** across the key metrics
  (revenue, margins, net profit, price/MT, gross profit/MT).
- Guards against impossible states (e.g. an assumption that drives revenue or a
  cost negative is rejected with a clear error).

### 4.4 Narrative / AI layer (`src/advisor/narrative/`)
Provider-agnostic; the LLM only ever sees `Facts`.

- **Advisor (`advisor.py`)** — Facts → `Advisory`: an executive summary, risk
  commentary, and a list of recommendations. With `fail_soft` it degrades to
  deterministic template prose so the app still produces output offline.
- **Conversational chat (`chat.py`)** — answer plain-English questions grounded
  in the computed Facts and prior conversation.
- **Provider abstraction (`client.py`, `factory.py`, `providers.py`)** — one
  `LLMClient` interface; backend selected by the `LLM_PROVIDER` env var.
  **Gemini** is the default (free tier, called over its REST API via `httpx` —
  no vendor SDK, so it stays offline-mockable and PyInstaller-friendly).
  OpenAI / Anthropic / Ollama are selectable.
- **Prompt safety (`context.py`, `templates.py`)** — builds a prompt-safe context
  from Facts and renders templated prompts; the API key is never logged or
  embedded in error messages.

### 4.5 Reports (`src/advisor/reports/`)
- **Excel workbook (`excel.py`, openpyxl)** — an enhanced, formatted workbook.
- **PDF board note (`pdf.py`, ReportLab)** — a printable board briefing.
- **Word memo (`word.py`, python-docx)** — an editable management memo.
- **Dashboard payload (`dashboard.py`)** — deterministic JSON (Decimals as
  strings, aligned period series) that feeds the on-screen charts and scorecard.
- **Report pack (`pack.py`)** — bundles the deliverables together.
- **Formatting (`formatting.py`)** — currency formatting, status colors, disclaimers.

### 4.6 API (`src/advisor/api/`) — FastAPI
| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness + version + active provider |
| `POST /api/upload` | Upload an income statement, create a session |
| `POST /api/analyze` | Build Facts + (optional) AI narrative + dashboard |
| `POST /api/scenario` | Run a what-if and return base-vs-scenario comparison |
| `POST /api/chat` | Ask a grounded question about the financials |
| `GET /api/export/{fmt}` | Download `excel` / `pdf` / `word` / `dashboard` |
| `DELETE /api/session/{id}` | Drop a session |

Sessions are held in an in-memory store; the static dashboard is served at `/`.

### 4.7 Desktop shell (`src/advisor/app.py`)
- Runs the FastAPI app under uvicorn on a free local port in a background thread.
- Opens a native **pywebview** window pointing at the local server.
- `--selfcheck` runs a headless verification (health + dashboard + bundled
  assets) used by the packaged-binary smoke test; it writes its result to both
  stdout and a sentinel file so the windowed `.exe` stays verifiable.

### 4.8 Front-end (`web/`) — vanilla, offline, no framework
Hand-built HTML/CSS/JS with hand-drawn canvas charts (no build step, no CDN).
Premium glassy aesthetic with light and dark themes.

- **Dashboard** — greeting, live **KPI scorecard**, revenue & margin trajectory
  chart, "board attention" anomaly list, revenue movement, plus inline **Scenario
  Lab**, **Ask the Committee**, and **Report pack** panels.
- **Executive Committee** — a panel of AI executive personas (CFO, Financial
  Controller, Operations Director, Procurement Expert, Risk Officer, Strategy
  Director), a **boardroom reasoning timeline**, a **committee consensus** view,
  and the ability to **design a custom advisor**.
- **Marketplace** — install additional specialist executives.
- **Settings** — appearance (light/dark), committee management, exports, and
  keyboard shortcuts.

---

## 5. Configuration & data

- **Thresholds (`config/thresholds.yaml`)** — all green/yellow cut-offs and
  anomaly limits live here as **user-editable data**, never baked into code.
  Covers margins (gross/operating/net), ratios (finance-cost-to-sales,
  opex-to-sales), and anomaly triggers (margin-drop bps, COGS-vs-sales gap,
  cost-spike %).
- **Secrets (`.env`)** — `LLM_PROVIDER` and the provider API key come from the
  environment only (gitignored). Never hardcoded, logged, or printed.

---

## 6. Engineering quality

- **Strict TDD** throughout — a failing test drives every piece of production code.
- **Coverage gates:** ≥90% overall, **100% on the engine**.
- **Tooling:** `ruff` (lint + format) clean, `mypy --strict` clean.
- **Single quality command:** `python scripts/check.py` runs format, lint, type
  check, and tests with the coverage gates.
- Current status: **321 tests passing**, ~96% overall coverage, engine at 100%.

---

## 7. Tech stack

Python 3.11 · FastAPI · uvicorn · pydantic v2 · pydantic-settings ·
pure Decimal financial engine · pywebview (native window) ·
vanilla HTML/CSS/JS + hand-drawn canvas charts · openpyxl (Excel) ·
ReportLab (PDF) · python-docx (Word) · httpx (LLM REST) ·
pytest / pytest-cov / pytest-mock · ruff · mypy · PyInstaller (single `.exe`).

---

## 8. Distribution

- Build: `python packaging/build.py` → `packaging/dist/"Master of Coin AI.exe"`.
- A clean, windowed (no-console) single file is also placed at the project root
  as `Master of Coin AI.exe` for double-click use.
- The whole folder can be handed over: the recipient double-clicks the `.exe`
  to run the app, and the full source (`src/`, `web/`, `config/`, `tests/`)
  remains available to inspect.

---

## 9. Vision

Start with one manufacturer's P&L. The architecture — a deterministic engine, an
AI narrative layer that explains but never invents, and pluggable executive
advisors — generalizes to any company's financials. The wedge is trust:
**the machine does the math, the AI does the language, and the two can never blur.**
