# Master of Coin AI — Documentation

**Master of Coin AI** is a standalone Windows desktop AI financial advisor for **any
company**. The company profile — name, parent group, reporting currency, volume
unit, and fiscal year end — is configured in `.env`, never hardcoded.

This document is the complete guide: how to run it, how to use every feature,
how it works under the hood, the API reference, and how to build and ship it.

- For the executive pitch / capability spec, see [PRODUCT_OVERVIEW.md](PRODUCT_OVERVIEW.md).
- For a one-page "how to open it", see `RUN THE APP.txt`.

---

## Table of contents

1. [What it does](#1-what-it-does)
2. [The trust model](#2-the-trust-model)
3. [Quick start (non-technical)](#3-quick-start-non-technical)
4. [Developer setup](#4-developer-setup)
5. [Configuration](#5-configuration)
6. [Using the app — feature by feature](#6-using-the-app--feature-by-feature)
7. [Input spreadsheet format](#7-input-spreadsheet-format)
8. [How it works — architecture](#8-how-it-works--architecture)
9. [The financial engine](#9-the-financial-engine)
10. [The AI narrative layer](#10-the-ai-narrative-layer)
11. [Reports & exports](#11-reports--exports)
12. [HTTP API reference](#12-http-api-reference)
13. [Configuration & thresholds reference](#13-configuration--thresholds-reference)
14. [Testing & quality gates](#14-testing--quality-gates)
15. [Building the Windows .exe](#15-building-the-windows-exe)
16. [Project layout](#16-project-layout)
17. [Troubleshooting & FAQ](#17-troubleshooting--faq)

---

## 1. What it does

Master of Coin AI reads an income statement, computes the financials **deterministically**,
has a large language model write the executive advisory layer on top, and
produces a full set of board-ready deliverables:

- An **enhanced Excel workbook** (KPIs, status, variance, anomalies).
- A **PDF board note**.
- A **Word memo**.
- An **interactive dashboard** with charts and a KPI scorecard.

It also offers a **Scenario Lab** (what-if analysis), an **Executive Committee**
of AI personas, and a **conversational chat** grounded in the computed numbers.

It ships as a single double-clickable Windows `.exe` and runs fully offline.

---

## 2. The trust model

This is the product's defining design decision.

| Layer | Responsibility | Hard constraint |
| --- | --- | --- |
| **Deterministic engine** | Computes *every* figure — KPIs, ratios, variances, anomalies, scenarios | Pure functions. No network, no LLM, no floats (Decimal only). Reproducible and auditable. |
| **AI narrative layer** | Writes the *words* — summaries, risk, recommendations, chat | Receives only a frozen `Facts` object. It never sees raw inputs and never does arithmetic. |

> **The machine does the math, the AI does the language, and the two can never blur.**

This separation is enforced by tests: the engine and ingestion packages are
asserted to import no network/LLM libraries, and the narrative layer is asserted
to receive only `Facts`, never the raw income statement that holds the figures.

---

## 3. Quick start (non-technical)

You do **not** need Python, VS Code, or any install.

1. Double-click **`Master of Coin AI.exe`** in this folder.
2. A desktop window opens with the dashboard.
3. Click **Upload statement** and choose an income-statement `.xlsx`.
4. Explore: KPI scorecard, charts, Scenario Lab, Executive Committee, and the
   one-click report exports.

First launch may take 10–20 seconds while it unpacks. If Windows SmartScreen
warns (the file isn't code-signed), click **More info → Run anyway**.

The app works offline. To enable the AI-written commentary, see
[Configuration](#5-configuration); without a key it falls back to deterministic
template prose and everything else still works.

---

## 4. Developer setup

Requires **Python 3.11+**.

```powershell
# from the project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # PowerShell (cmd: .venv\Scripts\activate.bat)
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run the app in development:

```powershell
master-of-coin           # launches the FastAPI server + native pywebview window
# or
python -m advisor.app
```

> Note: `master-of-coin` is the internal package/console-script name. The
> user-facing product is **Master of Coin AI** (window title, UI, reports).

---

## 5. Configuration

### LLM provider (`.env`)

Copy `.env.example` to `.env` and fill in a key (only needed for AI commentary):

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

Supported `LLM_PROVIDER` values: `gemini` (default, free tier), `openai`,
`anthropic`, `ollama`. Optional tuning variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `gemini` | Which backend to use |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | — | Provider key (per provider) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama endpoint (no key) |
| `LLM_MODEL` | provider default | Override the model name |
| `LLM_TEMPERATURE` | `0.0` | Sampling temperature |
| `LLM_TIMEOUT` | `30.0` | Request timeout (seconds) |

Keys are read from the environment only, are never logged, and never appear in
error messages. The `.env` file is gitignored.

### Company profile (`.env`)

These variables brand the reports, prompts, and dashboard for your company:

| Variable | Default | Purpose |
| --- | --- | --- |
| `COMPANY_NAME` | `Your Company` | Company name on reports and in prompts |
| `GROUP_NAME` | *(empty)* | Parent group, shown alongside the company when set |
| `CURRENCY` | `USD` | Reporting currency code used in all formatted output |
| `VOLUME_UNIT` | `MT` | Unit for sales volume and per-unit economics |
| `FISCAL_YEAR_END_MONTH` | `12` | Month the fiscal year ends (12 = calendar year, 6 = July–June) |

### Thresholds (`config/thresholds.yaml`)

All green/yellow cut-offs and anomaly limits are **user-editable data**, never
baked into code. See [Configuration & thresholds reference](#13-configuration--thresholds-reference).

---

## 6. Using the app — feature by feature

### Dashboard
- **Welcome band** — greeting + the trust-model statement.
- **KPI scorecard** — the latest period's metrics with red/amber/green status.
- **Revenue & margin trajectory** — multi-period charts.
- **Board attention** — flagged anomalies with their numbers.
- Inline **Scenario Lab**, **Ask the Committee**, and **Report pack** panels.

### Scenario Lab (what-if)
Adjust assumptions — revenue, COGS, **price per MT**, **volume**, opex, finance
cost — and instantly see a base-vs-scenario comparison, all recomputed
deterministically. Impossible inputs (e.g. driving revenue negative) are rejected
with a clear message.

### Executive Committee
A panel of AI executive personas (CFO, Financial Controller, Operations Director,
Procurement Expert, Risk Officer, Strategy Director) reason over the numbers,
with a **boardroom reasoning timeline** and a **committee consensus** view. You
can **design a custom advisor** and install more from the **Marketplace**.

### Conversational chat
Ask plain-English questions ("How are margins trending?") and get answers
grounded in the computed Facts.

### Reports
One click each to download the Excel workbook, PDF board note, Word memo, or the
dashboard JSON payload.

### Settings
Appearance (light/dark), committee management, exports, and keyboard shortcuts.

---

## 7. Input spreadsheet format

Master of Coin AI ingests an Excel income statement. It is tolerant of real-world
layouts: it auto-detects the reporting scale (e.g. thousands / lakh / crore),
maps inconsistent labels to a canonical schema, and recognizes period columns.

The easiest way to start is the **blank template**: click *Excel template* next
to Upload in the app (or `GET /api/template`), or take
[`examples/income_statement_template.xlsx`](examples/income_statement_template.xlsx)
from the repository. Its *Instructions* sheet lists every recognised label and
period format.

A minimal example (the first column is line labels; each following column is a
reporting period):

| Particulars | FY2022-23 | FY2023-24 |
| --- | --- | --- |
| Revenue | 2,000,000,000 | 2,480,000,000 |
| Cost of Goods Sold | 1,200,000,000 | 1,910,000,000 |
| Sales Volume (MT) | 16,000 | 18,500 |

Recognized concepts include revenue, COGS, gross profit, operating expenses
(selling/distribution, administrative, other), operating profit, other income,
finance cost, profit before tax, tax, net profit, and sales volume (MT).
Subtotals that are present are validated for consistency; missing subtotals are
derived by the engine.

---

## 8. How it works — architecture

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
        ├──────────────► [ Scenario engine ]  what-if deltas → base-vs-scenario
        │
        ▼
[ Narrative ]  Facts → Advisory (summary, risk, recommendations) + chat
        │
        ▼
[ Reports ]    Excel · PDF · Word · dashboard JSON
        │
        ▼
[ Desktop ]    FastAPI (served at /) + pywebview native window
```

- **`src/advisor/ingestion/`** — spreadsheet → canonical `IncomeStatement`.
- **`src/advisor/engine/`** — pure deterministic math (100% test coverage).
- **`src/advisor/narrative/`** — provider-agnostic LLM adapter + prompts.
- **`src/advisor/reports/`** — Excel / PDF / Word / dashboard generators.
- **`src/advisor/api/`** — FastAPI HTTP layer + in-memory session store.
- **`src/advisor/app.py`** — desktop launcher (uvicorn thread + pywebview window).
- **`web/`** — vanilla HTML/CSS/JS dashboard (no framework, no build step).

---

## 9. The financial engine

All money/volume values are `Decimal`; there are no floats in the value path.

**Per-period KPIs** (`engine/kpis.py`):
- Subtotals: revenue, COGS, gross profit, total opex, operating profit, other
  income, finance cost, profit before tax, tax, net profit, volume (MT).
- Ratios: gross / operating / net margin %, COGS-to-sales %, opex-to-sales %,
  finance-cost-to-sales %.
- Per-MT economics: selling price per MT, COGS per MT, gross profit per MT.

**Variance** (`engine/variance.py`) — period-over-period change with basis
support (sequential / MoM / QoQ / YoY) and direction (up / down / flat).

**Anomaly detection** (`engine/anomaly.py`) — rule-based, emitting stable codes,
severity (info / warning / critical), and the exact numeric context. Driven by
the `anomalies` section of the thresholds file:
- Margin drop beyond a basis-point threshold vs the prior period.
- COGS growth outpacing sales growth beyond a percentage-point gap.
- Any cost line spiking beyond a percentage threshold.

**Status bands** (`engine/status.py`) — traffic-light scoring (green / yellow /
red / unknown) against the editable thresholds, honoring "higher is better" vs
"lower is better".

**Scenario engine** (`engine/scenario.py`) — applies assumption deltas
(percentage / absolute / set) to targets (revenue, COGS, finance cost, other
income, tax, opex sub-lines, price/MT, volume), re-runs the Facts build on a
copy (the base is never mutated), and returns a structured comparison. Invalid
transforms (e.g. negative revenue/cost) raise a clear error.

The engine assembles everything into an immutable **`Facts`** graph — the single
hand-off to the AI layer.

---

## 10. The AI narrative layer

- **Advisory** (`narrative/advisor.py`) — turns `Facts` into an executive
  summary, risk commentary, and recommendations. With `fail_soft` it degrades to
  deterministic template prose so output is always produced offline.
- **Chat** (`narrative/chat.py`) — grounded Q&A over the Facts and history.
- **Provider abstraction** (`client.py`, `factory.py`, `providers.py`) — one
  `LLMClient` interface; the backend is chosen by `LLM_PROVIDER`. Gemini is the
  default, called over its REST API via `httpx` (no vendor SDK, so it stays
  offline-mockable and PyInstaller-friendly). In tests the LLM is always mocked.

The LLM only ever receives a prompt-safe context built from `Facts`; it cannot
read the raw income statement.

---

## 11. Reports & exports

| Format | Module | Library | Contents |
| --- | --- | --- | --- |
| Excel | `reports/excel.py` | openpyxl | Cover, Income Statement, KPIs, Status, Variance, Anomalies sheets |
| PDF | `reports/pdf.py` | ReportLab | Board note: summary, scorecard, risk, recommendations, anomalies |
| Word | `reports/word.py` | python-docx | Memo: summary, KPI table, recommendations |
| Dashboard | `reports/dashboard.py` | — | Deterministic JSON for the on-screen charts |

PDF bytes are deterministic (same input + timestamp → identical bytes). All
outputs are formatted in the configured currency and carry the standard disclaimer.

---

## 12. HTTP API reference

Base prefix: `/api`. The desktop app serves the static dashboard at `/` and
talks to these endpoints. Sessions are held in an in-memory store.

### `GET /api/health`
Returns liveness, version, and the active provider.
```json
{ "status": "ok", "version": "0.1.0", "provider": "gemini" }
```

### `POST /api/upload`  (multipart, field `file`)
Uploads an income-statement `.xlsx`, creates a session.
```json
{
  "session_id": "…",
  "summary": {
    "company_name": "Acme Manufacturing Ltd.",
    "currency": "USD", "volume_unit": "MT",
    "n_periods": 2,
    "periods": [ { "label": "FY2022-23", "period_type": "year", "fiscal_year": 2022, "sequence": 0 } ],
    "source_file": null
  },
  "warnings": []
}
```

### `POST /api/analyze`
Builds the Facts (and, by default, the AI narrative) and a dashboard payload.
```json
// request
{ "session_id": "…", "include_narrative": true }
// response → { session_id, facts, narrative, dashboard }
```

### `POST /api/scenario`
Runs a what-if and returns a base-vs-scenario comparison.
```json
// request
{
  "session_id": "…",
  "name": "What-if",
  "assumptions": {
    "revenue_pct": null, "cogs_pct": "8", "price_per_mt_pct": null,
    "volume_pct": null, "opex_pct": null, "finance_cost_pct": null,
    "period_label": null
  },
  "include_narrative": false
}
// response → { session_id, scenario_facts, comparison, dashboard }
```

### `POST /api/chat`
Grounded Q&A. Requires the session to be analyzed first.
```json
// request
{ "session_id": "…", "message": "How are margins?" }
// response → { session_id, reply, history: [ { role, content } ] }
```

### `GET /api/export/{fmt}?session_id=…`
`fmt` ∈ `excel | pdf | word | dashboard`. Streams the file (or JSON for
`dashboard`). Requires an analyzed session.

### `DELETE /api/session/{session_id}`
Drops the session (204 No Content).

**Errors** are returned as `{ "code": "...", "detail": "..." }`, e.g.
`session_not_found` (404) or `not_analyzed` (409, call `/api/analyze` first).

---

## 13. Configuration & thresholds reference

`config/thresholds.yaml` (current defaults):

```yaml
margins:
  gross_margin_pct:     { green: 18.0, yellow: 12.0, direction: higher_is_better }
  operating_margin_pct: { green: 10.0, yellow: 5.0,  direction: higher_is_better }
  net_margin_pct:       { green: 6.0,  yellow: 2.0,  direction: higher_is_better }
ratios:
  finance_cost_to_sales_pct: { green: 3.0, yellow: 6.0,  direction: lower_is_better }
  opex_to_sales_pct:         { green: 8.0, yellow: 12.0, direction: lower_is_better }
anomalies:
  margin_drop_bps: 200              # flag a margin drop > 200 bps vs prior period
  cogs_vs_sales_growth_gap_pct: 3.0 # flag COGS growth outpacing sales by > 3 pts
  cost_spike_pct: 15.0              # flag any cost line growing > 15% vs prior
```

- `direction: higher_is_better` → green if value ≥ green; yellow if ≥ yellow;
  else red. `lower_is_better` is the inverse.
- Edit these values to retune the scorecard and anomaly sensitivity; no code
  change or rebuild is required.

---

## 14. Testing & quality gates

Strict TDD throughout. A single command runs everything:

```powershell
python scripts/check.py
```

It runs `ruff format --check`, `ruff check`, `mypy --strict`, and `pytest` with
coverage. Gates: **≥90% overall** and **100% on the engine**. Current status:
**321 tests passing**, ~96% overall coverage, engine at 100%.

Run tests alone with `pytest`. The LLM is always mocked in tests, so they are
deterministic and offline.

---

## 15. Building the Windows .exe

```powershell
pip install -e ".[package]"
python packaging/build.py            # → packaging/dist/"Master of Coin AI.exe"
```

The build is a single windowed file (no console window). A clean,
double-clickable copy is published at the project root as **`Master of Coin AI.exe`**.

Headless verification (used by the packaged-binary smoke test):

```powershell
"Master of Coin AI.exe" --selfcheck        # prints SELFCHECK OK and exits 0
```

`--selfcheck` boots the server in-process, checks `/api/health` and the
dashboard, confirms the bundled `config/thresholds.yaml` is present, and writes
the result to both stdout and a sentinel file (so the windowed build stays
verifiable).

To hand the project off: zip and send the whole folder. The recipient
double-clicks `Master of Coin AI.exe`; the full source remains available to inspect.

---

## 16. Project layout

```
Master of Coin AI.exe          # clickable demo build (windowed)
RUN THE APP.txt          # one-page run guide for recipients
README.md                # dev quick start
PRODUCT_OVERVIEW.md      # product & capability spec / pitch
DOCUMENTATION.md         # this file
config/thresholds.yaml   # editable thresholds (user data)
src/advisor/
  app.py                 # desktop launcher (uvicorn + pywebview)
  config.py              # settings + thresholds loader
  schema.py              # canonical pydantic models + frozen Facts
  ingestion/             # spreadsheet → canonical IncomeStatement
  engine/                # PURE deterministic: kpis, variance, anomaly, scenario, status
  narrative/             # provider-agnostic LLM adapter + prompts
  reports/               # excel, pdf, word, dashboard, pack
  api/                   # FastAPI routes, models, sessions
web/                     # static dashboard (index.html, styles.css, app.js)
tests/                   # unit / integration / e2e
packaging/               # PyInstaller spec + build script
scripts/check.py         # format + lint + type-check + tests + coverage
```

---

## 17. Troubleshooting & FAQ

**The window opens then closes / nothing happens when I run `python -m advisor.app`.**
That's the dev launcher; it prints nothing and exits when the window closes. For
the demo, run `Master of Coin AI.exe` instead.

**SmartScreen blocks the .exe.**
The binary isn't code-signed. Click **More info → Run anyway**. (For production,
sign the binary with a code-signing certificate.)

**No AI commentary appears.**
You have no LLM key configured, so the app is in degraded mode — every number is
still computed and shown; only the AI-written prose falls back to templates. Add
a key in `.env` to enable it.

**Upload fails or numbers look off.**
Check that the file is a real `.xlsx` income statement with a label column and
one column per period. The ingestion layer auto-detects scale and labels, but a
radically different layout may need the labels recognized — see
[Input spreadsheet format](#7-input-spreadsheet-format).

**Can I change the red/amber/green bands?**
Yes — edit `config/thresholds.yaml`. No rebuild needed.

**Does it need the internet?**
No. It runs fully offline. Internet is only used if you configure a cloud LLM
provider for the AI commentary.

**Currency / units.**
Reporting currency, volume unit, and fiscal year end are configured per deployment via `.env` (defaults: USD / MT / calendar year).
```
