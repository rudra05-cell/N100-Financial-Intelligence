-- =============================================================
-- Nifty 100 Financial Intelligence Platform
-- notebooks/exploratory_queries.sql
-- Sprint 1 · Day 07 · 10 Exploratory Queries
-- Run against: data/nifty100.db
-- sqlite3 data/nifty100.db < notebooks/exploratory_queries.sql
-- =============================================================

-- ─────────────────────────────────────────────────────────────
-- Q01: Total company count (exit criterion: must be 92)
-- ─────────────────────────────────────────────────────────────
SELECT 'Q01: Company Count' AS query_name,
       COUNT(*) AS total_companies
FROM companies;

-- ─────────────────────────────────────────────────────────────
-- Q02: Row counts per time-series table
-- ─────────────────────────────────────────────────────────────
SELECT 'Q02: P&L rows'         AS table_name, COUNT(*) AS row_count FROM profitandloss
UNION ALL
SELECT 'Q02: BS rows',          COUNT(*) FROM balancesheet
UNION ALL
SELECT 'Q02: CF rows',          COUNT(*) FROM cashflow
UNION ALL
SELECT 'Q02: stock_prices rows',COUNT(*) FROM stock_prices
UNION ALL
SELECT 'Q02: fin_ratios rows',  COUNT(*) FROM financial_ratios;

-- ─────────────────────────────────────────────────────────────
-- Q03: Year coverage per company (how many years of P&L data)
-- Shows min, max, avg years across all companies
-- ─────────────────────────────────────────────────────────────
SELECT 'Q03: Year Coverage' AS query_name,
       MIN(yr_count)  AS min_years,
       MAX(yr_count)  AS max_years,
       ROUND(AVG(yr_count), 1) AS avg_years,
       COUNT(CASE WHEN yr_count < 5 THEN 1 END) AS companies_under_5yr
FROM (
    SELECT company_id, COUNT(DISTINCT year) AS yr_count
    FROM profitandloss
    GROUP BY company_id
);

-- ─────────────────────────────────────────────────────────────
-- Q04: Companies with less than 5 years of P&L data (DQ-16 flag)
-- ─────────────────────────────────────────────────────────────
SELECT 'Q04: Companies < 5yr P&L' AS note,
       p.company_id,
       c.company_name,
       COUNT(DISTINCT p.year) AS yr_count
FROM profitandloss p
LEFT JOIN companies c ON p.company_id = c.id
GROUP BY p.company_id
HAVING COUNT(DISTINCT p.year) < 5
ORDER BY yr_count ASC;

-- ─────────────────────────────────────────────────────────────
-- Q05: NULL / missing value counts in key P&L columns
-- High null % = data quality concern for ratio engine
-- ─────────────────────────────────────────────────────────────
SELECT 'Q05: P&L Nulls' AS query_name,
       COUNT(*) AS total_rows,
       SUM(CASE WHEN sales           IS NULL THEN 1 ELSE 0 END) AS null_sales,
       SUM(CASE WHEN net_profit      IS NULL THEN 1 ELSE 0 END) AS null_net_profit,
       SUM(CASE WHEN operating_profit IS NULL THEN 1 ELSE 0 END) AS null_op_profit,
       SUM(CASE WHEN eps              IS NULL THEN 1 ELSE 0 END) AS null_eps
FROM profitandloss;

-- ─────────────────────────────────────────────────────────────
-- Q06: NULL counts in Balance Sheet key columns
-- ─────────────────────────────────────────────────────────────
SELECT 'Q06: BS Nulls' AS query_name,
       COUNT(*) AS total_rows,
       SUM(CASE WHEN total_assets      IS NULL THEN 1 ELSE 0 END) AS null_total_assets,
       SUM(CASE WHEN total_liabilities IS NULL THEN 1 ELSE 0 END) AS null_total_liab,
       SUM(CASE WHEN borrowings        IS NULL THEN 1 ELSE 0 END) AS null_borrowings,
       SUM(CASE WHEN equity_capital    IS NULL THEN 1 ELSE 0 END) AS null_equity_cap
FROM balancesheet;

-- ─────────────────────────────────────────────────────────────
-- Q07: Sector distribution — companies per broad sector
-- ─────────────────────────────────────────────────────────────
SELECT 'Q07: Sector Distribution' AS query_name,
       s.broad_sector,
       COUNT(*) AS company_count
FROM sectors s
GROUP BY s.broad_sector
ORDER BY company_count DESC;

-- ─────────────────────────────────────────────────────────────
-- Q08: Top 10 companies by latest-year revenue (sales)
-- Quick sanity check — Reliance, TCS, HDFC Bank should appear
-- ─────────────────────────────────────────────────────────────
SELECT 'Q08: Top 10 by Revenue' AS query_name,
       p.company_id,
       c.company_name,
       p.year,
       ROUND(p.sales, 0) AS sales_cr
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = (
    SELECT MAX(year) FROM profitandloss p2
    WHERE p2.company_id = p.company_id
)
ORDER BY p.sales DESC
LIMIT 10;

-- ─────────────────────────────────────────────────────────────
-- Q09: FK integrity check — orphan rows in child tables
-- All counts must be 0 for the exit criterion to pass
-- ─────────────────────────────────────────────────────────────
SELECT 'Q09: FK Orphans in P&L' AS check_name,
       COUNT(*) AS orphan_count
FROM profitandloss
WHERE company_id NOT IN (SELECT id FROM companies)
UNION ALL
SELECT 'Q09: FK Orphans in BS',
       COUNT(*) FROM balancesheet
WHERE company_id NOT IN (SELECT id FROM companies)
UNION ALL
SELECT 'Q09: FK Orphans in CF',
       COUNT(*) FROM cashflow
WHERE company_id NOT IN (SELECT id FROM companies);

-- ─────────────────────────────────────────────────────────────
-- Q10: Sample 5 companies — year range and row count
-- Manual review reference for Day 06 DQ check
-- ─────────────────────────────────────────────────────────────
SELECT 'Q10: Sample Company Year Ranges' AS query_name,
       p.company_id,
       c.company_name,
       MIN(p.year) AS earliest_year,
       MAX(p.year) AS latest_year,
       COUNT(DISTINCT p.year) AS total_years,
       ROUND(AVG(p.sales), 0) AS avg_sales_cr
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.company_id IN ('TCS', 'HDFCBANK', 'RELIANCE', 'INFY', 'HINDUNILVR')
GROUP BY p.company_id, c.company_name
ORDER BY p.company_id;
