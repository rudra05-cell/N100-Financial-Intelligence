"""
src/analytics/cagr.py
Day 10 — CAGR Engine.
Computes Revenue, PAT, and EPS CAGR over 3Y / 5Y / 10Y windows.
All 6 edge cases are handled; a flag column is stored alongside each value.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── CAGR flag constants ───────────────────────────────────────────────────────
FLAG_NORMAL        = None
FLAG_TURNAROUND    = "TURNAROUND"
FLAG_DECLINE       = "DECLINE_TO_LOSS"
FLAG_BOTH_NEG      = "BOTH_NEGATIVE"
FLAG_ZERO_BASE     = "ZERO_BASE"
FLAG_INSUFFICIENT  = "INSUFFICIENT"


def cagr(start_val: float, end_val: float, n_years: int) -> tuple[Optional[float], Optional[str]]:
    """
    CAGR = ((end / start) ^ (1/n) − 1) × 100.
    Returns (value, flag).

    Edge cases:
      n < 3                       → (None, INSUFFICIENT)
      start = 0                   → (None, ZERO_BASE)
      start < 0, end > 0          → (None, TURNAROUND)
      start > 0, end < 0          → (None, DECLINE_TO_LOSS)
      start < 0, end < 0          → (None, BOTH_NEGATIVE)
      start > 0, end > 0          → (value, None)  — normal
    """
    if n_years < 3:
        return None, FLAG_INSUFFICIENT
    if start_val is None or end_val is None:
        return None, FLAG_INSUFFICIENT
    if start_val == 0:
        return None, FLAG_ZERO_BASE
    if start_val < 0 and end_val > 0:
        return None, FLAG_TURNAROUND
    if start_val > 0 and end_val < 0:
        return None, FLAG_DECLINE
    if start_val < 0 and end_val < 0:
        return None, FLAG_BOTH_NEG
    # Normal: both positive
    result = ((end_val / start_val) ** (1 / n_years) - 1) * 100
    return round(result, 4), FLAG_NORMAL


def compute_cagr_series(
    series: pd.Series,
    year_series: pd.Series,
    windows: tuple[int, ...] = (3, 5, 10),
) -> dict[str, Optional[float]]:
    """
    Given a time-ordered pandas Series of values and corresponding year labels,
    compute CAGR for each window (3Y, 5Y, 10Y).

    Returns a dict:
      { 'cagr_3yr': float|None, 'cagr_3yr_flag': str|None,
        'cagr_5yr': float|None, 'cagr_5yr_flag': str|None,
        'cagr_10yr': float|None, 'cagr_10yr_flag': str|None }
    """
    result = {}
    # Sort by year
    df = pd.DataFrame({"year": year_series, "val": series}).sort_values("year").dropna(subset=["val"])

    latest_val = df["val"].iloc[-1] if len(df) > 0 else None

    for n in windows:
        key = f"cagr_{n}yr"
        if len(df) > n:
            base_val = df["val"].iloc[-(n + 1)]
            val, flag = cagr(base_val, latest_val, n)
        else:
            val, flag = None, FLAG_INSUFFICIENT
        result[key]            = val
        result[f"{key}_flag"]  = flag

    return result


def compute_all_cagrs_for_company(
    pl_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Given a company's full P&L history (sorted by year), compute CAGR columns
    for each year row (using that year as the 'end' point).

    Adds columns:
      revenue_cagr_3yr, revenue_cagr_3yr_flag
      revenue_cagr_5yr, revenue_cagr_5yr_flag
      revenue_cagr_10yr, revenue_cagr_10yr_flag
      pat_cagr_3yr, pat_cagr_3yr_flag
      pat_cagr_5yr, pat_cagr_5yr_flag
      pat_cagr_10yr, pat_cagr_10yr_flag
      eps_cagr_5yr, eps_cagr_5yr_flag

    Returns augmented DataFrame.
    """
    pl = pl_df.sort_values("year").reset_index(drop=True)

    windows = (3, 5, 10)
    metrics = [
        ("sales",      "revenue_cagr"),
        ("net_profit", "pat_cagr"),
        ("eps",        "eps_cagr"),
    ]

    # Initialise output columns
    for _, prefix in metrics:
        for n in windows:
            if prefix == "eps_cagr" and n != 5:
                continue   # EPS CAGR only for 5Y per spec
            pl[f"{prefix}_{n}yr"]      = None
            pl[f"{prefix}_{n}yr_flag"] = None

    for i in range(len(pl)):
        end_row = pl.iloc[i]
        for metric_col, prefix in metrics:
            for n in windows:
                if prefix == "eps_cagr" and n != 5:
                    continue
                key       = f"{prefix}_{n}yr"
                flag_key  = f"{prefix}_{n}yr_flag"
                if i < n:
                    pl.at[i, key]      = None
                    pl.at[i, flag_key] = FLAG_INSUFFICIENT
                    continue
                base_row  = pl.iloc[i - n]
                start_val = base_row.get(metric_col)
                end_val   = end_row.get(metric_col)
                if pd.isna(start_val) or pd.isna(end_val):
                    pl.at[i, key]      = None
                    pl.at[i, flag_key] = FLAG_INSUFFICIENT
                    continue
                val, flag = cagr(float(start_val), float(end_val), n)
                pl.at[i, key]      = val
                pl.at[i, flag_key] = flag

    return pl
