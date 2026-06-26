"""
src/etl/validator.py
Data Quality (DQ) validation engine.
Implements all 16 DQ rules defined in Section 14 of the project spec.
Outputs a validation_failures.csv for analyst review.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING  = "WARNING"
SEVERITY_INFO     = "INFO"


def run_all_dq_rules(
    companies:       pd.DataFrame,
    profitandloss:   pd.DataFrame,
    balancesheet:    pd.DataFrame,
    cashflow:        pd.DataFrame,
    output_path:     str = "output/validation_failures.csv",
) -> pd.DataFrame:
    """
    Run all 16 DQ rules against the loaded DataFrames.
    Returns a DataFrame of all failures.
    Writes failures to output_path CSV.
    """
    failures: list[dict] = []

    failures += _dq01_company_pk_uniqueness(companies)
    failures += _dq02_annual_pk_uniqueness(profitandloss, balancesheet, cashflow)
    failures += _dq03_fk_integrity(companies, profitandloss, balancesheet, cashflow)
    failures += _dq04_bs_balance(balancesheet)
    failures += _dq05_opm_crosscheck(profitandloss)
    failures += _dq06_positive_sales(profitandloss)
    failures += _dq07_year_format(profitandloss, balancesheet, cashflow)
    failures += _dq08_ticker_format(companies, profitandloss, balancesheet, cashflow)
    failures += _dq09_net_cash_check(cashflow)
    failures += _dq10_nonneg_fixed_assets(balancesheet)
    failures += _dq11_tax_rate_range(profitandloss)
    failures += _dq12_dividend_payout_cap(profitandloss)
    failures += _dq14_eps_sign(profitandloss)
    failures += _dq16_coverage_check(profitandloss, balancesheet, cashflow)

    df_failures = pd.DataFrame(failures)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_failures.to_csv(output_path, index=False)

    critical_count = len(df_failures[df_failures["severity"] == SEVERITY_CRITICAL])
    warning_count  = len(df_failures[df_failures["severity"] == SEVERITY_WARNING])

    logger.info(
        "DQ validation complete: %d CRITICAL, %d WARNING failures. "
        "Written to %s",
        critical_count, warning_count, output_path,
    )

    if critical_count > 0:
        logger.error(
            "HALT: %d CRITICAL DQ failures found. Resolve before loading DB.",
            critical_count,
        )

    return df_failures


# ──────────────────────────────────────────────────────────────────────────────
# Individual DQ Rule Implementations
# ──────────────────────────────────────────────────────────────────────────────

def _fail(rule_id, company_id, year, field, issue, severity) -> dict:
    """Helper to build a failure record."""
    return {
        "rule_id":    rule_id,
        "company_id": company_id,
        "year":       year,
        "field":      field,
        "issue":      issue,
        "severity":   severity,
    }


def _dq01_company_pk_uniqueness(companies: pd.DataFrame) -> list[dict]:
    """DQ-01: companies.id must be unique (no duplicate tickers)."""
    failures = []
    dupes = companies[companies.duplicated("id", keep=False)]
    for _, row in dupes.iterrows():
        failures.append(_fail(
            "DQ-01", row["id"], None, "id",
            f"Duplicate company ticker: {row['id']}",
            SEVERITY_CRITICAL,
        ))
    return failures


def _dq02_annual_pk_uniqueness(pl, bs, cf) -> list[dict]:
    """DQ-02: (company_id, year) must be unique in P&L, BS, CF tables."""
    failures = []
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        if "company_id" not in df.columns or "year" not in df.columns:
            continue
        dupes = df[df.duplicated(["company_id", "year"], keep=False)]
        for _, row in dupes.iterrows():
            failures.append(_fail(
                "DQ-02", row["company_id"], row.get("year"), "company_id+year",
                f"Duplicate (company_id, year) in {name}",
                SEVERITY_CRITICAL,
            ))
    return failures


def _dq03_fk_integrity(companies, pl, bs, cf) -> list[dict]:
    """DQ-03: All company_id values in child tables must exist in companies.id."""
    failures = []
    valid_ids = set(companies["id"].dropna().str.strip().str.upper())
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        if "company_id" not in df.columns:
            continue
        orphans = df[~df["company_id"].isin(valid_ids)]
        for _, row in orphans.iterrows():
            failures.append(_fail(
                "DQ-03", row["company_id"], row.get("year"), "company_id",
                f"Orphan company_id '{row['company_id']}' not in companies table (table: {name})",
                SEVERITY_CRITICAL,
            ))
    return failures


def _dq04_bs_balance(bs: pd.DataFrame) -> list[dict]:
    """DQ-04: |total_assets - total_liabilities| / total_assets < 1%."""
    failures = []
    for _, row in bs.iterrows():
        ta = row.get("total_assets")
        tl = row.get("total_liabilities")
        if ta is None or tl is None or pd.isna(ta) or pd.isna(tl):
            continue
        if ta == 0:
            continue
        diff_pct = abs(ta - tl) / abs(ta)
        if diff_pct >= 0.01:
            failures.append(_fail(
                "DQ-04", row["company_id"], row.get("year"),
                "total_assets/total_liabilities",
                f"BS imbalance: assets={ta:.2f}, liabilities={tl:.2f}, diff={diff_pct:.2%}",
                SEVERITY_WARNING,
            ))
    return failures


def _dq05_opm_crosscheck(pl: pd.DataFrame) -> list[dict]:
    """DQ-05: |opm_percentage - (op_profit/sales*100)| < 1.0."""
    failures = []
    for _, row in pl.iterrows():
        opm_src = row.get("opm_percentage")
        op      = row.get("operating_profit")
        sales   = row.get("sales")
        if any(v is None or (isinstance(v, float) and pd.isna(v))
               for v in [opm_src, op, sales]):
            continue
        if sales == 0:
            continue
        opm_calc = (op / sales) * 100
        diff = abs(opm_src - opm_calc)
        if diff > 1.0:
            failures.append(_fail(
                "DQ-05", row["company_id"], row.get("year"), "opm_percentage",
                f"OPM mismatch: source={opm_src:.2f}%, computed={opm_calc:.2f}%, diff={diff:.2f}%",
                SEVERITY_WARNING,
            ))
    return failures


def _dq06_positive_sales(pl: pd.DataFrame) -> list[dict]:
    """DQ-06: sales must be > 0 for all non-bank companies."""
    failures = []
    for _, row in pl.iterrows():
        sales = row.get("sales")
        if sales is not None and not pd.isna(sales) and sales <= 0:
            failures.append(_fail(
                "DQ-06", row["company_id"], row.get("year"), "sales",
                f"Non-positive sales value: {sales}",
                SEVERITY_WARNING,
            ))
    return failures


def _dq07_year_format(pl, bs, cf) -> list[dict]:
    """DQ-07: After normalisation, year must match YYYY-MM."""
    failures = []
    pattern = re.compile(r"^\d{4}-\d{2}$")
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        if "year" not in df.columns:
            continue
        bad = df[~df["year"].astype(str).str.match(r"^\d{4}-\d{2}$")]
        for _, row in bad.iterrows():
            failures.append(_fail(
                "DQ-07", row.get("company_id"), row.get("year"), "year",
                f"Unparseable year value '{row['year']}' in {name}",
                SEVERITY_CRITICAL,
            ))
    return failures


def _dq08_ticker_format(companies, pl, bs, cf) -> list[dict]:
    """DQ-08: company_id length must be 2-12 chars after normalisation."""
    failures = []
    all_dfs = [("companies", companies, "id")]
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        all_dfs.append((name, df, "company_id"))

    for name, df, col in all_dfs:
        if col not in df.columns:
            continue
        bad = df[df[col].astype(str).str.len().lt(2) |
                 df[col].astype(str).str.len().gt(12)]
        for _, row in bad.iterrows():
            failures.append(_fail(
                "DQ-08", row.get(col), row.get("year"), col,
                f"Ticker '{row[col]}' has invalid length in {name}",
                SEVERITY_CRITICAL,
            ))
    return failures


def _dq09_net_cash_check(cf: pd.DataFrame) -> list[dict]:
    """DQ-09: |net_cash_flow - (CFO+CFI+CFF)| <= 10 Cr."""
    failures = []
    for _, row in cf.iterrows():
        cfo = row.get("operating_activity")
        cfi = row.get("investing_activity")
        cff = row.get("financing_activity")
        ncf = row.get("net_cash_flow")
        if any(v is None or (isinstance(v, float) and pd.isna(v))
               for v in [cfo, cfi, cff, ncf]):
            continue
        computed = cfo + cfi + cff
        diff = abs(ncf - computed)
        if diff > 10:
            failures.append(_fail(
                "DQ-09", row["company_id"], row.get("year"), "net_cash_flow",
                f"Net cash mismatch: source={ncf:.2f}, computed={computed:.2f}, diff={diff:.2f} Cr",
                SEVERITY_WARNING,
            ))
    return failures


def _dq10_nonneg_fixed_assets(bs: pd.DataFrame) -> list[dict]:
    """DQ-10: fixed_assets must be >= 0."""
    failures = []
    for _, row in bs.iterrows():
        fa = row.get("fixed_assets")
        if fa is not None and not pd.isna(fa) and fa < 0:
            failures.append(_fail(
                "DQ-10", row["company_id"], row.get("year"), "fixed_assets",
                f"Negative fixed_assets: {fa}. Will be coerced to 0.",
                SEVERITY_WARNING,
            ))
    return failures


def _dq11_tax_rate_range(pl: pd.DataFrame) -> list[dict]:
    """DQ-11: tax_percentage must be in [0, 60]."""
    failures = []
    for _, row in pl.iterrows():
        tax = row.get("tax_percentage")
        if tax is not None and not pd.isna(tax):
            if not (0 <= tax <= 60):
                failures.append(_fail(
                    "DQ-11", row["company_id"], row.get("year"), "tax_percentage",
                    f"Tax rate out of range [0,60]: {tax}%. May be deferred tax reversal.",
                    SEVERITY_WARNING,
                ))
    return failures


def _dq12_dividend_payout_cap(pl: pd.DataFrame) -> list[dict]:
    """DQ-12: dividend_payout > 200% is likely a data entry error."""
    failures = []
    for _, row in pl.iterrows():
        dp = row.get("dividend_payout")
        if dp is not None and not pd.isna(dp) and dp > 200:
            failures.append(_fail(
                "DQ-12", row["company_id"], row.get("year"), "dividend_payout",
                f"Dividend payout {dp}% exceeds 200%. Likely data error.",
                SEVERITY_WARNING,
            ))
    return failures


def _dq14_eps_sign(pl: pd.DataFrame) -> list[dict]:
    """DQ-14: EPS must be > 0 if net_profit > 0."""
    failures = []
    for _, row in pl.iterrows():
        eps = row.get("eps")
        np_ = row.get("net_profit")
        if any(v is None or (isinstance(v, float) and pd.isna(v)) for v in [eps, np_]):
            continue
        if np_ > 0 and eps <= 0:
            failures.append(_fail(
                "DQ-14", row["company_id"], row.get("year"), "eps",
                f"EPS={eps} is not positive despite net_profit={np_:.2f} Cr.",
                SEVERITY_WARNING,
            ))
    return failures


def _dq16_coverage_check(pl, bs, cf) -> list[dict]:
    """DQ-16: Each company should have >= 5 years of records."""
    failures = []
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        if "company_id" not in df.columns:
            continue
        coverage = df.groupby("company_id")["year"].nunique()
        short = coverage[coverage < 5]
        for company_id, yr_count in short.items():
            failures.append(_fail(
                "DQ-16", company_id, None, "year",
                f"Only {yr_count} years of data in {name} (min 5 required for CAGR).",
                SEVERITY_WARNING,
            ))
    return failures
