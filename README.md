<!-- Banner -->
<div align="center">

# 🇮🇳 Nifty 100 Financial Intelligence Platform

**Production-grade fundamental analysis engine for India's 92 largest listed companies.**  
Built end-to-end in Python — ETL · KPI Engine · Screener · Health Scoring · Dashboard · REST API

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-136%20passing-brightgreen)](reports/pytest_report.html)
[![License](https://img.shields.io/badge/License-Internal%20Use-orange)](.)

</div>

---

## What This Is

This platform transforms 12 raw Excel datasets (7 core + 5 supplementary) into a fully queryable financial intelligence system covering **92 Nifty 100 companies** across **10–13 years of annual history**.

It is designed and built as a **placement-grade data analytics capstone** — every module is production-coded with tests, logging, edge case handling, and documentation.

> **Currency standard:** All monetary values in **Indian Rupees — Crore (₹ Cr)** unless stated otherwise.

---

## Platform at a Glance

| Metric | Value |
|--------|-------|
| Companies covered | **92** (Nifty 100 index constituents) |
| Years of history per company | **10–13 years** (FY2011–FY2024) |
| Financial KPIs computed | **50+** |
| Database tables | **10** |
| Total data records | **~11,000+** |
| Unit tests | **136 passing** |
| Analytics modules | **12** |
| Screener filters | **18** |
| Peer groups | **11** |
| Broad sectors | **11** |
| Build timeline | **45 days / 6 sprints** |

---

## Architecture

```
Raw Excel Files (12)
       │
       ▼
┌─────────────────────────────────────┐
│  L1  Data Ingestion (loader.py)     │  openpyxl · pandas
│  L2  ETL & Normalisation            │  normaliser.py · validator.py
│  L3  SQLite Database (10 tables)    │  nifty100.db · WAL mode · FK constraints
│  L4  Analytics Engine               │  ratios.py · cagr.py · cashflow_kpis.py
│  L5  Intelligence Layer             │  screener · health score · peer comparison
│  L6  Reporting Layer                │  ReportLab PDFs · openpyxl Excel
│  L7  Dashboard & API                │  Streamlit · FastAPI · Uvicorn
└─────────────────────────────────────┘
```

---

## Sprint Roadmap

| Sprint | Days | Theme | Status |
|--------|------|-------|--------|
| **Sprint 1** | 1–7 | Data Foundation & ETL | ✅ **Complete** |
| **Sprint 2** | 8–14 | Financial Ratio Engine (50+ KPIs) | ✅ **Complete** |
| Sprint 3 | 15–21 | Screener · Health Scoring · Sector Analytics | 🔄 Next |
| Sprint 4 | 22–28 | Dashboard · Valuation Module | ⏳ |
| Sprint 5 | 29–35 | Intelligence · PDF Reports | ⏳ |
| Sprint 6 | 36–45 | REST API · ML Clustering · QA | ⏳ |

---

## Sprint 1 — Data Foundation ✅

**Goal:** Load all 12 datasets into a clean, FK-validated SQLite database.

### What was built

| File | Purpose |
|------|---------|
| `src/etl/loader.py` | Reads all 12 Excel files with `header=1` (core) / `header=0` (supplementary), normalises, validates, and loads into SQLite |
| `src/etl/normaliser.py` | Converts any year label (`Mar-23`, `FY24`, `Dec-22`, `2023`, `TTM` → excluded) to `YYYY-MM`; upper-strips all NSE tickers |
| `src/etl/validator.py` | Runs all 16 DQ rules; outputs `validation_failures.csv` with severity |
| `db/schema.sql` | 10-table SQLite schema with FK constraints, WAL journal, and indexes |
| `tests/etl/test_normalise.py` | 41 unit tests for normaliser edge cases |
| `tests/dq/test_rules.py` | 28 unit tests — one "passes" + one "triggers" per DQ rule |

### Database tables

| Table | Rows | Description |
|-------|------|-------------|
| `companies` | 92 | Master reference — NSE ticker, name, sector metadata |
| `profitandloss` | 1,161 | Annual P&L — sales, EBITDA, PAT, EPS, OPM% |
| `balancesheet` | 1,220 | Annual BS — equity, debt, assets, investments |
| `cashflow` | 1,152 | Annual CF — CFO, CFI, CFF, net cash flow |
| `analysis` | 20 | Pre-computed text growth metrics (Screener.in) |
| `documents` | 1,585 | Annual report PDF links (BSE India) |
| `prosandcons` | 16 | Qualitative investment insights |
| `sectors` | 92 | GICS-style sector mapping (11 broad, 33 sub) |
| `stock_prices` | 5,520 | Monthly OHLCV — Jan 2020 to Dec 2024 |
| `financial_ratios` | 1,118 | **Computed KPIs** — 25+ columns per company-year |

### Data Quality Rules (16)

| Rule | Check | Severity |
|------|-------|----------|
| DQ-01 | Company ticker uniqueness | CRITICAL |
| DQ-02 | (company_id, year) PK uniqueness | CRITICAL |
| DQ-03 | FK integrity — all company_ids exist | CRITICAL |
| DQ-04 | Balance sheet balances within 1% | WARNING |
| DQ-05 | OPM% cross-check vs formula | WARNING |
| DQ-06 | Sales > 0 for non-banks | WARNING |
| DQ-07 | Year format after normalisation = `YYYY-MM` | CRITICAL |
| DQ-08 | Ticker length 2–12 chars | CRITICAL |
| DQ-09 | Net cash flow = CFO + CFI + CFF ± ₹10 Cr | WARNING |
| DQ-10 | Fixed assets ≥ 0 | WARNING |
| DQ-11 | Tax rate 0–60% | WARNING |
| DQ-12 | Dividend payout ≤ 200% | WARNING |
| DQ-14 | EPS > 0 if net profit > 0 | WARNING |
| DQ-16 | Each company has ≥ 5 years of data | WARNING |

### Sprint 1 Exit Criteria — All Passed

```
SELECT COUNT(*) FROM companies       → 92   ✅
PRAGMA foreign_key_check             → 0    ✅
load_audit.csv CRITICAL rejections   → 0    ✅
Unit tests passing                   → 69   ✅  (41 normaliser + 28 DQ)
Manual review: 5 companies correct   → Done ✅
```

---

## Sprint 2 — Financial Ratio Engine ✅

**Goal:** Compute 50+ KPIs for all 92 companies × all available years.

### KPIs Computed

**Profitability**
| KPI | Formula | Edge Case |
|-----|---------|-----------|
| Net Profit Margin | `net_profit / sales × 100` | None if sales = 0 |
| Operating Profit Margin | `operating_profit / sales × 100` | Cross-validated vs source OPM% |
| Return on Equity (ROE) | `net_profit / (equity + reserves) × 100` | None if equity ≤ 0 |
| Return on Capital (ROCE) | `EBIT / (equity + reserves + borrowings) × 100` | Bank sector carve-out |
| Return on Assets (ROA) | `net_profit / total_assets × 100` | None if assets = 0 |

**Leverage**
| KPI | Formula | Edge Case |
|-----|---------|-----------|
| Debt-to-Equity | `borrowings / (equity + reserves)` | 0 if debt-free; flag if > 5× (non-financials) |
| Interest Coverage | `(EBITDA + other_income) / interest` | None → label "Debt Free" if interest = 0 |
| Net Debt | `borrowings − investments` | Negative = net cash positive |

**Growth (CAGR Engine)**

6 edge cases handled for every CAGR computation:

| Base | End | Result | Flag |
|------|-----|--------|------|
| > 0 | > 0 | Computed | — |
| < 0 | > 0 | None | `TURNAROUND` |
| > 0 | < 0 | None | `DECLINE_TO_LOSS` |
| < 0 | < 0 | None | `BOTH_NEGATIVE` |
| 0 | Any | None | `ZERO_BASE` |
| < 3yr data | — | None | `INSUFFICIENT` |

**Cash Flow Intelligence**
| KPI | What It Tells You |
|-----|-------------------|
| Free Cash Flow (FCF) | Cash left after all investment — the truest measure of business quality |
| CFO Quality Score | Is profit real cash or just accounting? (CFO/PAT > 1.0 = High Quality) |
| CapEx Intensity | Asset-light (<3%) vs Capital Intensive (>8%) |
| FCF Conversion Rate | What % of EBITDA becomes actual cash |
| Capital Allocation Pattern | One of 8 patterns: Reinvestor / Distress / Growth by Debt / etc. |

**Composite Quality Score (0–100)**

Weighted composite used for screener ranking:
```
35% Profitability  (ROE 15% + ROCE 10% + NPM 10%)
30% Cash Quality   (FCF CAGR 15% + CFO/PAT 10% + FCF>0 flag 5%)
20% Growth         (Revenue CAGR 5yr 10% + PAT CAGR 5yr 10%)
15% Leverage       (D/E score 10% + ICR score 5%)
```

### Sprint 2 Exit Criteria — All Passed

```
SELECT COUNT(*) FROM financial_ratios  → 1,118   ✅  (≥1,100 required)
KPI formula tests passing              → 136     ✅  (≥20 required)
ROE spot-check TCS/HDFCBANK/HINDUNILVR → 0.0000% diff  ✅
Revenue CAGR 5yr spot-check            → <0.0001% diff  ✅
Screener preview (ROE>15%, D/E<1)      → 39 companies   ✅  (15–50 required)
ratio_edge_cases.log                   → 110 anomalies documented  ✅
```

---

## Quick Start

```bash
# 1. Clone / unzip the project
cd nifty100

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux

# 3. Install all dependencies (~20 libraries)
pip install -r requirements.txt

# 4. Copy environment config
cp config/.env.template .env

# 5. Run ETL — loads all 12 Excel files → nifty100.db
python src/etl/loader.py

# 6. Run Ratio Engine — computes 50+ KPIs for all companies
python src/analytics/run_ratios.py

# 7. Run test suite — should show 136 passed
python -m pytest tests/ -v

# 8. Launch dashboard (Sprint 5)
streamlit run src/dashboard/app.py

# 9. Launch REST API (Sprint 6)
uvicorn src.api.main:app --port 8000
```

### Makefile shortcuts

```bash
make load       # ETL: load all 12 files → nifty100.db
make ratios     # Compute 50+ KPIs → financial_ratios table
make test       # Full pytest suite → reports/pytest_report.html
make dashboard  # Streamlit on localhost:8501
make api        # FastAPI on localhost:8000/docs
make clean      # Remove build artifacts
```

---

## Project Structure

```
nifty100/
│
├── data/
│   ├── raw/                    ← 7 core Excel files  [READ ONLY]
│   │   ├── companies.xlsx
│   │   ├── profitandloss.xlsx
│   │   ├── balancesheet.xlsx
│   │   ├── cashflow.xlsx
│   │   ├── analysis.xlsx
│   │   ├── documents.xlsx
│   │   └── prosandcons.xlsx
│   ├── supporting/             ← 5 supplementary files
│   │   ├── sectors.xlsx
│   │   ├── stock_prices.xlsx
│   │   ├── market_cap.xlsx
│   │   ├── financial_ratios.xlsx
│   │   └── peer_groups.xlsx
│   └── nifty100.db             ← SQLite database (built by make load)
│
├── src/
│   ├── etl/
│   │   ├── loader.py           ← Reads all 12 Excel files; normalises; loads SQLite
│   │   ├── normaliser.py       ← Year + ticker normalisation (TTM excluded)
│   │   └── validator.py        ← 16 DQ rules; outputs validation_failures.csv
│   ├── analytics/
│   │   ├── ratios.py           ← NPM, OPM, ROE, ROCE, ROA, D/E, ICR, AT, BVPS
│   │   ├── cagr.py             ← CAGR engine: Revenue/PAT/EPS × 3Y/5Y/10Y
│   │   ├── cashflow_kpis.py    ← FCF, CFO Quality, CapEx Intensity, Capital Allocation
│   │   └── run_ratios.py       ← Orchestrator: runs full engine → populates DB
│   ├── dashboard/              ← Streamlit app (Sprint 4–5)
│   ├── api/                    ← FastAPI 16-endpoint server (Sprint 6)
│   ├── reports/                ← PDF/Excel generators (Sprint 5)
│   └── nlp/                    ← Pros/cons generator (Sprint 5)
│
├── tests/
│   ├── etl/test_normalise.py   ← 41 tests: year + ticker normalisation
│   ├── dq/test_rules.py        ← 28 tests: all 16 DQ rules
│   └── kpi/
│       ├── test_ratios.py      ← 16 formula tests (pre-Sprint 2)
│       └── test_sprint2.py     ← 45 tests: ratios.py + cagr.py + cashflow_kpis.py
│
├── output/
│   ├── load_audit.csv          ← Per-table row counts and rejection stats
│   ├── validation_failures.csv ← All DQ violations with severity
│   ├── capital_allocation.csv  ← 1,152 company-year capital allocation labels
│   ├── ratio_edge_cases.log    ← 110 KPI anomalies documented
│   ├── sprint1_dq_review.md    ← Day 06 manual review of 5 companies
│   ├── sprint1_retro.md        ← Sprint 1 retrospective
│   └── sprint2_retro.md        ← Sprint 2 retrospective
│
├── db/schema.sql               ← 10-table SQLite schema with FK + indexes
├── notebooks/exploratory_queries.sql  ← 10 analytical SQL queries
├── reports/pytest_report.html  ← 136-test HTML report
├── config/.env.template        ← Environment config template
├── requirements.txt            ← 20 pinned dependencies
├── Makefile                    ← load / ratios / test / dashboard / api / clean
└── README.md                   ← This file
```

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Data | pandas | ≥ 2.0 | DataFrame operations, Excel I/O |
| Data | NumPy | ≥ 1.24 | Vectorised KPI computation |
| Data | openpyxl | ≥ 3.1 | Read `.xlsx` with `header=1` |
| Database | SQLite | 3.x | Single-file relational DB; zero config |
| Analytics | scipy | ≥ 1.11 | Statistical distributions, hypothesis tests |
| Analytics | scikit-learn | ≥ 1.3 | KMeans clustering, percentile ranking |
| Visualisation | Plotly | ≥ 5.18 | Interactive charts (dashboard) |
| Visualisation | matplotlib | ≥ 3.7 | Static charts for PDF reports |
| Dashboard | Streamlit | ≥ 1.30 | 8-screen analyst web app |
| API | FastAPI | ≥ 0.110 | 16-endpoint REST API |
| API | Uvicorn | ≥ 0.27 | ASGI server |
| Reporting | ReportLab | ≥ 4.1 | PDF generation (92 tearsheets) |
| NLP | NLTK | ≥ 3.8 | Pros/cons generation |
| Testing | pytest | ≥ 7.4 | Unit test framework |
| Dev | black | ≥ 24.0 | Code formatting (PEP 8) |
| Dev | ruff | ≥ 0.4 | Linting |

---

## Key SQL Queries

```sql
-- Top 10 companies by latest ROE
SELECT r.company_id, c.company_name, r.return_on_equity_pct
FROM financial_ratios r JOIN companies c ON r.company_id = c.id
WHERE r.year = (SELECT MAX(year) FROM financial_ratios r2 WHERE r2.company_id = r.company_id)
ORDER BY r.return_on_equity_pct DESC LIMIT 10;

-- Quality screener: ROE > 15%, D/E < 1, FCF positive
SELECT company_id, return_on_equity_pct, debt_to_equity, free_cash_flow_cr
FROM financial_ratios
WHERE return_on_equity_pct > 15 AND debt_to_equity < 1 AND free_cash_flow_cr > 0;

-- Sector median ROE
SELECT s.broad_sector, ROUND(AVG(r.return_on_equity_pct), 1) AS median_roe
FROM financial_ratios r JOIN sectors s ON r.company_id = s.company_id
GROUP BY s.broad_sector ORDER BY median_roe DESC;

-- Capital allocation pattern distribution
SELECT pattern_label, COUNT(*) as companies
FROM capital_allocation
WHERE year = (SELECT MAX(year) FROM capital_allocation)
GROUP BY pattern_label ORDER BY companies DESC;
```

---

## Sectors Covered

| Broad Sector | Companies | Example Tickers |
|-------------|-----------|----------------|
| Financials | 23 | HDFCBANK, SBIN, ICICIBANK, KOTAKBANK |
| Energy | 15 | RELIANCE, ONGC, NTPC, ADANIGREEN |
| Consumer Discretionary | 12 | MARUTI, TATAMOTORS, M&M, TRENT |
| Industrials | 9 | LT, HAL, BEL, SIEMENS |
| Consumer Staples | 8 | HINDUNILVR, ITC, BRITANNIA, NESTLEIND |
| Materials | 8 | TATASTEEL, JSWSTEEL, HINDALCO, SHREECEM |
| Information Technology | 6 | TCS, INFY, HCLTECH, TECHM |
| Healthcare | 5 | SUNPHARMA, CIPLA, DRREDDY, DIVISLAB |
| Real Estate | 3 | DLF, LODHA |
| Communication | 2 | BHARTIARTL |
| Conglomerates | 5 | BAJAJHLDNG |

---

## Health Score Bands (Sprint 3)

| Score | Band | Meaning |
|-------|------|---------|
| 80–100 | 🟢 Excellent | Top-tier: high ROE, low debt, strong FCF |
| 65–79 | 🟡 Good | Above average across most metrics |
| 50–64 | 🟠 Average | Mixed profile — some strengths, some risks |
| 35–49 | 🔴 Weak | Below-average quality; monitoring required |
| 0–34 | ⚫ Poor | Distress signals; high leverage or negative FCF |

---

## Acceptance Criteria Progress

| Gate | Description | Status |
|------|-------------|--------|
| AC-01 | 92 companies in DB | ✅ |
| AC-02 | ≥90% companies with ≥10yr P&L | ✅ |
| AC-03 | FK check = 0 violations | ✅ |
| AC-04 | financial_ratios ≥ 1,100 rows | ✅ 1,118 |
| AC-05 | Revenue CAGR spot-check ±0.1% | ✅ <0.0001% |
| AC-06 | ROE spot-check ±5% | ✅ 0.0000% |
| AC-07 | Screener returns 15–50 companies | ✅ 39 |
| AC-18 | ≥60 tests, 0 failures | ✅ 136 tests |
| AC-19 | validation_failures.csv exists | ✅ |

---

## Built By

**Rudra** — Data Analytics Engineering Intern  
*Nifty 100 Financial Intelligence Platform · 45-Day Capstone · June 2026*  
*Data Analytics Division · Internal Use Only · v1.0*

---

*All monetary values in ₹ Crore unless stated otherwise.*  
*Stock price and market cap datasets are simulated for educational purposes.*
