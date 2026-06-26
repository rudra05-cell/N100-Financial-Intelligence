-- =============================================================
-- Nifty 100 Financial Intelligence Platform
-- db/schema.sql  |  Version 1.0  |  10-Table SQLite Schema
-- =============================================================
-- Run:  sqlite3 data/nifty100.db < db/schema.sql
-- All monetary values in Indian Rupees — Crore (₹ Cr)
-- =============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─────────────────────────────────────────────────────────────
-- TABLE 1: companies  (master reference — 92 rows)
-- PK: id (NSE ticker, e.g. TCS, HDFCBANK)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS companies (
    id                VARCHAR(12)  PRIMARY KEY,   -- NSE ticker — strip + upper on load
    company_name      VARCHAR(200) NOT NULL,
    company_logo      TEXT,
    chart_link        TEXT,
    about_company     TEXT,
    website           TEXT,
    nse_profile       TEXT,
    bse_profile       TEXT,
    face_value        NUMERIC,
    book_value        NUMERIC,
    roce_percentage   NUMERIC,
    roe_percentage    NUMERIC
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 2: profitandloss  (annual P&L — ~1,276 rows)
-- PK: (company_id, year)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profitandloss (
    id                  INTEGER,
    company_id          VARCHAR(12)  NOT NULL REFERENCES companies(id),
    year                VARCHAR(7)   NOT NULL,   -- normalised: YYYY-MM
    sales               NUMERIC,                 -- ₹ Cr — must be > 0
    expenses            NUMERIC,
    operating_profit    NUMERIC,
    opm_percentage      NUMERIC,
    other_income        NUMERIC,
    interest            NUMERIC,
    depreciation        NUMERIC,
    profit_before_tax   NUMERIC,
    tax_percentage      NUMERIC,
    net_profit          NUMERIC,
    eps                 NUMERIC,
    dividend_payout     NUMERIC,
    PRIMARY KEY (company_id, year)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 3: balancesheet  (annual BS — ~1,312 rows)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS balancesheet (
    id                  INTEGER,
    company_id          VARCHAR(12)  NOT NULL REFERENCES companies(id),
    year                VARCHAR(7)   NOT NULL,
    equity_capital      NUMERIC,
    reserves            NUMERIC,
    borrowings          NUMERIC,
    other_liabilities   NUMERIC,
    total_liabilities   NUMERIC,
    fixed_assets        NUMERIC,
    cwip                NUMERIC,
    investments         NUMERIC,
    other_asset         NUMERIC,
    total_assets        NUMERIC,
    PRIMARY KEY (company_id, year)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 4: cashflow  (annual CF — ~1,187 rows)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cashflow (
    id                      INTEGER,
    company_id              VARCHAR(12)  NOT NULL REFERENCES companies(id),
    year                    VARCHAR(7)   NOT NULL,
    operating_activity      NUMERIC,     -- CFO — positive = good
    investing_activity      NUMERIC,     -- CFI — negative = investing in growth
    financing_activity      NUMERIC,     -- CFF
    net_cash_flow           NUMERIC,     -- = CFO + CFI + CFF
    PRIMARY KEY (company_id, year)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 5: analysis  (pre-computed growth text — ~20 rows)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analysis (
    id                          INTEGER PRIMARY KEY,
    company_id                  VARCHAR(12)  NOT NULL REFERENCES companies(id),
    compounded_sales_growth     TEXT,
    compounded_profit_growth    TEXT,
    stock_price_cagr            TEXT,
    roe                         TEXT
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 6: documents  (annual report links — ~1,585 rows)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY,
    company_id      VARCHAR(12)  NOT NULL REFERENCES companies(id),
    Year            INTEGER      NOT NULL,   -- calendar year (note capital Y)
    Annual_Report   TEXT
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 7: prosandcons  (qualitative insights — ~16 rows)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prosandcons (
    id          INTEGER PRIMARY KEY,
    company_id  VARCHAR(12)  NOT NULL REFERENCES companies(id),
    pros        TEXT,
    cons        TEXT
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 8: sectors  (sector mapping — 92 rows)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sectors (
    company_id              VARCHAR(12)  PRIMARY KEY REFERENCES companies(id),
    broad_sector            VARCHAR(50),
    sub_sector              VARCHAR(100),
    index_weight_pct        NUMERIC,
    market_cap_category     VARCHAR(20)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 9: stock_prices  (monthly OHLCV — 5,520 rows, SIMULATED)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_prices (
    company_id      VARCHAR(12)  NOT NULL REFERENCES companies(id),
    date            VARCHAR(10)  NOT NULL,   -- YYYY-MM-DD (1st of month)
    open_price      NUMERIC,
    high_price      NUMERIC,
    low_price       NUMERIC,
    close_price     NUMERIC,
    volume          INTEGER,
    adjusted_close  NUMERIC,
    PRIMARY KEY (company_id, date)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE 10: financial_ratios  (computed KPIs — ~1,184 rows)
-- Built by Sprint 2 Ratio Engine — do NOT manually edit
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id                      VARCHAR(12)  NOT NULL REFERENCES companies(id),
    year                            VARCHAR(7)   NOT NULL,
    -- Profitability
    net_profit_margin_pct           NUMERIC,
    operating_profit_margin_pct     NUMERIC,
    return_on_equity_pct            NUMERIC,
    return_on_capital_pct           NUMERIC,
    return_on_assets_pct            NUMERIC,
    -- Leverage
    debt_to_equity                  NUMERIC,
    interest_coverage               NUMERIC,
    net_debt_cr                     NUMERIC,
    -- Efficiency
    asset_turnover                  NUMERIC,
    -- Cash Flow
    free_cash_flow_cr               NUMERIC,
    capex_cr                        NUMERIC,
    cash_from_operations_cr         NUMERIC,
    -- Per Share
    earnings_per_share              NUMERIC,
    book_value_per_share            NUMERIC,
    dividend_payout_ratio_pct       NUMERIC,
    total_debt_cr                   NUMERIC,
    -- Growth (populated by CAGR engine in Sprint 2)
    revenue_cagr_3yr                NUMERIC,
    revenue_cagr_5yr                NUMERIC,
    revenue_cagr_10yr               NUMERIC,
    pat_cagr_3yr                    NUMERIC,
    pat_cagr_5yr                    NUMERIC,
    eps_cagr_5yr                    NUMERIC,
    -- Flags
    cagr_flag                       VARCHAR(30), -- TURNAROUND / DECLINE_TO_LOSS / etc.
    capital_allocation_pattern      VARCHAR(30), -- Reinvestor / Distress / etc.
    PRIMARY KEY (company_id, year)
);

-- ─────────────────────────────────────────────────────────────
-- INDEXES for common query patterns
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_pl_company   ON profitandloss (company_id);
CREATE INDEX IF NOT EXISTS idx_bs_company   ON balancesheet  (company_id);
CREATE INDEX IF NOT EXISTS idx_cf_company   ON cashflow      (company_id);
CREATE INDEX IF NOT EXISTS idx_fr_company   ON financial_ratios (company_id);
CREATE INDEX IF NOT EXISTS idx_fr_year      ON financial_ratios (year);
CREATE INDEX IF NOT EXISTS idx_sp_company   ON stock_prices  (company_id);
CREATE INDEX IF NOT EXISTS idx_doc_company  ON documents     (company_id);

-- ─────────────────────────────────────────────────────────────
-- VERIFICATION QUERIES (run after load to confirm)
-- ─────────────────────────────────────────────────────────────
-- SELECT COUNT(*) FROM companies;          -- expect 92
-- SELECT COUNT(*) FROM profitandloss;      -- expect ~1276
-- SELECT COUNT(*) FROM balancesheet;       -- expect ~1312
-- SELECT COUNT(*) FROM cashflow;           -- expect ~1187
-- SELECT COUNT(*) FROM stock_prices;       -- expect 5520
-- PRAGMA foreign_key_check;               -- expect 0 rows
