"""
src/analytics/run_ratios.py
Day 12 — Populate financial_ratios table in SQLite.
Runs the full ratio engine for all 92 companies × all available years.
Computes 17 KPI columns + CAGR columns + composite quality score.

Usage:
    python src/analytics/run_ratios.py
    OR: make ratios
"""

import logging
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "etl"))

from ratios import (
    net_profit_margin, operating_profit_margin, opm_crosscheck,
    return_on_equity, return_on_capital_employed, return_on_assets,
    debt_to_equity, interest_coverage_ratio, net_debt, asset_turnover,
    book_value_per_share,
)
from cagr import compute_all_cagrs_for_company
from cashflow_kpis import (
    free_cash_flow, capex_intensity, fcf_conversion_rate,
    classify_capital_allocation, compute_capital_allocation_for_all,
)

load_dotenv(dotenv_path="config/.env.template")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH    = os.getenv("DB_PATH", "data/nifty100.db")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
Path(OUTPUT_DIR).mkdir(exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Composite Quality Score
# ──────────────────────────────────────────────────────────────────────────────

def _winsorise(series: pd.Series, p_low: float = 10, p_high: float = 90) -> pd.Series:
    lo = series.quantile(p_low / 100)
    hi = series.quantile(p_high / 100)
    return series.clip(lo, hi)


def _scale_0_100(series: pd.Series) -> pd.Series:
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series([50.0] * len(series), index=series.index)
    return (series - mn) / (mx - mn) * 100


def _de_score(de: float) -> float:
    """D/E → 0–100 score (lower debt = higher score)."""
    if de is None or pd.isna(de):
        return 50.0
    if de == 0:
        return 100.0
    if de <= 0.5:
        return 85.0
    if de <= 1.0:
        return 70.0
    if de <= 2.0:
        return 50.0
    if de <= 5.0:
        return 25.0
    return 0.0


def _icr_score(icr) -> float:
    """ICR → 0–100 score. None (Debt Free) = 100."""
    if icr is None or pd.isna(icr):
        return 100.0
    if icr >= 10:
        return 100.0
    if icr >= 5:
        return 75.0
    if icr >= 3:
        return 50.0
    if icr >= 1.5:
        return 25.0
    return 0.0


def compute_composite_score(df: pd.DataFrame) -> pd.Series:
    """
    Composite Quality Score (0–100):
      35% Profitability (ROE 15%, ROCE 10%, NPM 10%)
      30% Cash Quality  (FCF_CAGR 15%, CFO/PAT 10%, FCF>0 flag 5%)
      20% Growth        (Revenue CAGR 5yr 10%, PAT CAGR 5yr 10%)
      15% Leverage      (D/E 10%, ICR 5%)
    """
    scores = pd.DataFrame(index=df.index)

    # Profitability
    for col in ["return_on_equity_pct", "return_on_capital_pct", "net_profit_margin_pct"]:
        s = pd.to_numeric(df[col], errors="coerce").fillna(df[col].median() if df[col].notna().any() else 0)
        scores[col] = _scale_0_100(_winsorise(s))

    # Growth
    for col in ["revenue_cagr_5yr", "pat_cagr_5yr"]:
        s = pd.to_numeric(df[col], errors="coerce").fillna(0)
        scores[col] = _scale_0_100(_winsorise(s))

    # Leverage
    scores["de_score"]  = df["debt_to_equity"].apply(_de_score)
    scores["icr_score"] = df["interest_coverage"].apply(_icr_score)

    # FCF flag (5% weight)
    fcf_flag = (pd.to_numeric(df["free_cash_flow_cr"], errors="coerce").fillna(0) > 0).astype(float) * 100

    composite = (
        scores["return_on_equity_pct"]    * 0.15 +
        scores["return_on_capital_pct"]   * 0.10 +
        scores["net_profit_margin_pct"]   * 0.10 +
        scores["revenue_cagr_5yr"]        * 0.10 +
        scores["pat_cagr_5yr"]            * 0.10 +
        fcf_flag                          * 0.05 +
        scores["de_score"]                * 0.10 +
        scores["icr_score"]               * 0.05
    )

    # Scale to 0–100
    composite = composite.clip(0, 100).round(2)
    return composite


# ──────────────────────────────────────────────────────────────────────────────
# Main Ratio Engine
# ──────────────────────────────────────────────────────────────────────────────

def run_ratio_engine():
    logger.info("=" * 60)
    logger.info("Sprint 2 — Ratio Engine Starting")
    logger.info("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    # ── Load all data ─────────────────────────────────────────────
    pl  = pd.read_sql("SELECT * FROM profitandloss",  conn)
    bs  = pd.read_sql("SELECT * FROM balancesheet",   conn)
    cf  = pd.read_sql("SELECT * FROM cashflow",       conn)
    co  = pd.read_sql("SELECT id, face_value FROM companies", conn)
    sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)

    logger.info("Loaded: P&L=%d  BS=%d  CF=%d  companies=%d", len(pl), len(bs), len(cf), len(co))

    # ── Merge all tables on (company_id, year) ────────────────────
    merged = (
        pl
        .merge(bs,  on=["company_id", "year"], how="inner", suffixes=("", "_bs"))
        .merge(cf,  on=["company_id", "year"], how="inner", suffixes=("", "_cf"))
        .merge(sec, left_on="company_id", right_on="company_id", how="left")
        .merge(co,  left_on="company_id", right_on="id", how="left")
    )
    logger.info("Merged rows: %d", len(merged))

    # ── Compute per-row ratios ────────────────────────────────────
    records = []
    edge_cases = []

    for _, row in merged.iterrows():
        cid   = row["company_id"]
        year  = row["year"]
        sector = row.get("broad_sector", "")

        npm = net_profit_margin(row.get("net_profit"), row.get("sales"))
        opm = operating_profit_margin(row.get("operating_profit"), row.get("sales"))
        roe = return_on_equity(row.get("net_profit"), row.get("equity_capital"), row.get("reserves"))
        roce = return_on_capital_employed(
            row.get("operating_profit"), row.get("depreciation"),
            row.get("equity_capital"), row.get("reserves"), row.get("borrowings")
        )
        roa = return_on_assets(row.get("net_profit"), row.get("total_assets"))
        de_ratio, high_lev = debt_to_equity(
            row.get("borrowings"), row.get("equity_capital"), row.get("reserves"), sector
        )
        icr_val, icr_label = interest_coverage_ratio(
            row.get("operating_profit"), row.get("other_income"), row.get("interest")
        )
        nd  = net_debt(row.get("borrowings"), row.get("investments"))
        at  = asset_turnover(row.get("sales"), row.get("total_assets"))
        bvps = book_value_per_share(
            row.get("equity_capital"), row.get("reserves"), row.get("face_value")
        )
        fcf = free_cash_flow(row.get("operating_activity"), row.get("investing_activity"))
        capex_pct, _ = capex_intensity(row.get("investing_activity"), row.get("sales"))
        fcf_conv = fcf_conversion_rate(fcf, row.get("operating_profit"))
        cfo_s, cfi_s, cff_s, cap_label = classify_capital_allocation(
            row.get("operating_activity"), row.get("investing_activity"), row.get("financing_activity")
        )

        # OPM cross-check for edge case log
        opm_diff = opm_crosscheck(
            row.get("opm_percentage"), row.get("operating_profit"), row.get("sales")
        )
        if opm_diff and opm_diff > 1.0 and sector != "Financials":
            edge_cases.append({
                "company_id": cid, "year": year,
                "metric": "OPM",
                "source_val": row.get("opm_percentage"),
                "computed_val": opm,
                "diff": opm_diff,
                "category": "Data source issue — bank NIM vs standard OPM" if sector == "Financials" else "OPM mismatch > 1%",
            })

        records.append({
            "company_id":                    cid,
            "year":                          year,
            "net_profit_margin_pct":         npm,
            "operating_profit_margin_pct":   opm,
            "return_on_equity_pct":          roe,
            "return_on_capital_pct":         roce,
            "return_on_assets_pct":          roa,
            "debt_to_equity":                de_ratio,
            "high_leverage_flag":            int(high_lev),
            "interest_coverage":             icr_val,
            "icr_label":                     icr_label,
            "net_debt_cr":                   nd,
            "asset_turnover":                at,
            "book_value_per_share":          bvps,
            "free_cash_flow_cr":             fcf,
            "capex_cr":                      abs(row.get("investing_activity") or 0),
            "capex_intensity_pct":           capex_pct,
            "fcf_conversion_rate":           fcf_conv,
            "cash_from_operations_cr":       row.get("operating_activity"),
            "total_debt_cr":                 row.get("borrowings"),
            "earnings_per_share":            row.get("eps"),
            "dividend_payout_ratio_pct":     row.get("dividend_payout"),
            "capital_allocation_pattern":    cap_label,
            # CAGR columns — filled next step
            "revenue_cagr_3yr":   None, "revenue_cagr_3yr_flag": None,
            "revenue_cagr_5yr":   None, "revenue_cagr_5yr_flag": None,
            "revenue_cagr_10yr":  None, "revenue_cagr_10yr_flag": None,
            "pat_cagr_3yr":       None, "pat_cagr_3yr_flag": None,
            "pat_cagr_5yr":       None, "pat_cagr_5yr_flag": None,
            "pat_cagr_10yr":      None, "pat_cagr_10yr_flag": None,
            "eps_cagr_5yr":       None, "eps_cagr_5yr_flag": None,
            "composite_quality_score": None,
        })

    ratios_df = pd.DataFrame(records)

    # ── Compute CAGRs per company (needs full history sorted) ─────
    logger.info("Computing CAGR for all companies...")
    cagr_rows = []
    for cid, grp in pl.groupby("company_id"):
        grp_sorted = grp.sort_values("year").reset_index(drop=True)
        augmented  = compute_all_cagrs_for_company(grp_sorted)
        cagr_cols  = [c for c in augmented.columns if "cagr" in c]
        cagr_sub   = augmented[["company_id", "year"] + cagr_cols]
        cagr_rows.append(cagr_sub)

    cagr_df = pd.concat(cagr_rows, ignore_index=True)
    ratios_df = ratios_df.merge(
        cagr_df, on=["company_id", "year"], how="left", suffixes=("", "_new")
    )
    # Prefer newly computed CAGR columns
    for col in [c for c in cagr_df.columns if c not in ("company_id", "year")]:
        new_col = f"{col}_new"
        if new_col in ratios_df.columns:
            ratios_df[col] = ratios_df[new_col].combine_first(ratios_df[col])
            ratios_df.drop(columns=[new_col], inplace=True)

    # ── Composite quality score ───────────────────────────────────
    logger.info("Computing composite quality scores...")
    ratios_df["composite_quality_score"] = compute_composite_score(ratios_df)

    # ── Write financial_ratios table ──────────────────────────────
    ratios_df.to_sql("financial_ratios", conn, if_exists="replace", index=False)
    conn.commit()

    row_count = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    logger.info("financial_ratios table: %d rows written", row_count)

    # ── Capital allocation CSV ────────────────────────────────────
    cap_alloc_df = compute_capital_allocation_for_all(cf)
    cap_path = f"{OUTPUT_DIR}/capital_allocation.csv"
    cap_alloc_df.to_csv(cap_path, index=False)
    logger.info("Capital allocation: %d rows → %s", len(cap_alloc_df), cap_path)

    # ── Edge cases log ────────────────────────────────────────────
    edge_path = f"{OUTPUT_DIR}/ratio_edge_cases.log"
    with open(edge_path, "w") as f:
        f.write("# Ratio Engine Edge Cases Log\n")
        f.write("# Sprint 2 — Financial Ratio Engine\n")
        f.write(f"# Total anomalies: {len(edge_cases)}\n\n")
        for ec in edge_cases:
            f.write(
                f"[{ec['company_id']}  {ec['year']}]  {ec['metric']}  "
                f"source={ec['source_val']:.2f}  computed={ec['computed_val']:.2f}  "
                f"diff={ec['diff']:.2f}  → {ec['category']}\n"
            )
    logger.info("Edge cases log: %d entries → %s", len(edge_cases), edge_path)

    # ── Bank ROCE cross-check (Day 13) ────────────────────────────
    companies_full = pd.read_sql("SELECT id, roce_percentage, roe_percentage FROM companies", conn)
    _run_crosschecks(ratios_df, companies_full, edge_path)

    # ── Sprint 2 exit: screener preview ──────────────────────────
    _screener_preview(ratios_df)

    logger.info("=" * 60)
    logger.info("RATIO ENGINE COMPLETE — %d rows in financial_ratios", row_count)
    logger.info("=" * 60)

    conn.close()
    return ratios_df


def _run_crosschecks(ratios_df: pd.DataFrame, companies_df: pd.DataFrame, log_path: str):
    """Day 13: Cross-check computed ROCE/ROE vs companies.xlsx pre-computed values."""
    latest = (
        ratios_df.sort_values("year")
        .groupby("company_id")
        .last()
        .reset_index()
    )
    merged = latest.merge(companies_df, left_on="company_id", right_on="id", how="left")
    anomalies = []

    for _, row in merged.iterrows():
        cid = row["company_id"]

        # ROCE cross-check
        src_roce = row.get("roce_percentage")
        eng_roce = row.get("return_on_capital_pct")
        if src_roce and eng_roce and not pd.isna(src_roce) and not pd.isna(eng_roce):
            diff = abs(float(src_roce) - float(eng_roce))
            if diff > 5:
                anomalies.append(
                    f"[{cid}]  ROCE  source={src_roce:.2f}  engine={eng_roce:.2f}  "
                    f"diff={diff:.2f}  → version_difference or bank_structure\n"
                )

        # ROE cross-check
        src_roe = row.get("roe_percentage")
        eng_roe = row.get("return_on_equity_pct")
        if src_roe and eng_roe and not pd.isna(src_roe) and not pd.isna(eng_roe):
            if float(src_roe) < 1.0:   # Anomalous source value (e.g. TCS shows 0.52)
                anomalies.append(
                    f"[{cid}]  ROE  source={src_roe}  engine={eng_roe:.2f}  "
                    f"→ anomalous_source_value (likely % vs decimal mismatch in companies.xlsx)\n"
                )

    with open(log_path, "a") as f:
        f.write(f"\n# ROCE/ROE Cross-Checks (Day 13) — {len(anomalies)} anomalies\n")
        for a in anomalies:
            f.write(a)

    logger.info("Cross-check complete: %d ROCE/ROE anomalies logged", len(anomalies))


def _screener_preview(ratios_df: pd.DataFrame):
    """Day 14 screener preview: ROE > 15% AND D/E < 1."""
    latest = (
        ratios_df.sort_values("year")
        .groupby("company_id")
        .last()
        .reset_index()
    )
    roe_num = pd.to_numeric(latest["return_on_equity_pct"], errors="coerce")
    de_num  = pd.to_numeric(latest["debt_to_equity"], errors="coerce")
    filtered = latest[(roe_num > 15) & (de_num < 1)]
    logger.info(
        "Screener preview (ROE>15%%, D/E<1): %d companies — %s",
        len(filtered),
        sorted(filtered["company_id"].tolist())
    )


if __name__ == "__main__":
    run_ratio_engine()
