"""
src/analytics/cashflow_kpis.py
Day 11 — Cash Flow KPIs & Capital Allocation Classifier.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CASH FLOW KPIs
# ══════════════════════════════════════════════════════════════════════════════

def free_cash_flow(operating_activity: float, investing_activity: float) -> float:
    """FCF = CFO + CFI. Negative allowed (investing heavily)."""
    return round((operating_activity or 0) + (investing_activity or 0), 4)


def cfo_quality_score(
    cfo_series: list[float], pat_series: list[float]
) -> tuple[Optional[float], str]:
    """
    CFO Quality Score = average(CFO / PAT) over up to 5 years.
    Returns (ratio, label):
      ratio > 1.0  → 'High Quality Earnings'
      0.5–1.0      → 'Moderate'
      < 0.5        → 'Accrual Risk'
      None         → 'Insufficient Data'
    Uses last min(5, len) years. Returns None if no valid pairs.
    """
    ratios = []
    pairs = list(zip(cfo_series[-5:], pat_series[-5:]))
    for cfo, pat in pairs:
        if pat and pat != 0 and cfo is not None:
            ratios.append(cfo / pat)

    if not ratios:
        return None, "Insufficient Data"

    avg = sum(ratios) / len(ratios)
    if avg > 1.0:
        label = "High Quality Earnings"
    elif avg >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return round(avg, 4), label


def capex_intensity(investing_activity: float, sales: float) -> tuple[Optional[float], str]:
    """
    CapEx Intensity = abs(investing_activity) / sales × 100.
    Note: investing_activity is used as CapEx proxy.
    Labels: <3% = Asset Light, 3–8% = Moderate, >8% = Capital Intensive.
    Returns (pct, label). None if sales = 0.
    """
    if not sales or sales == 0:
        return None, "Unknown"
    capex = abs(investing_activity or 0)
    pct = round(capex / sales * 100, 4)
    if pct < 3:
        label = "Asset Light"
    elif pct <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"
    return pct, label


def fcf_conversion_rate(fcf: float, operating_profit: float) -> Optional[float]:
    """
    FCF Conversion = FCF / operating_profit × 100.
    None if operating_profit = 0.
    >60% = Efficient, <30% = Heavy CapEx burden.
    """
    if not operating_profit or operating_profit == 0:
        return None
    return round(fcf / operating_profit * 100, 4)


# ══════════════════════════════════════════════════════════════════════════════
# CAPITAL ALLOCATION CLASSIFIER  (8-pattern)
# ══════════════════════════════════════════════════════════════════════════════

def _sign(val: float) -> str:
    """Return '+' if val >= 0 else '-'."""
    return "+" if (val or 0) >= 0 else "-"


# Pattern → label map (CFO_sign, CFI_sign, CFF_sign)
CAPITAL_ALLOCATION_PATTERNS: dict[tuple[str, str, str], str] = {
    ("+", "-", "-"): "Reinvestor",          # Ops fund capex + debt repay / dividends
    ("+", "-", "+"): "Mixed",               # Ops fund capex, also raising finance
    ("+", "+", "-"): "Liquidating Assets",  # Selling assets + paying debt
    ("+", "+", "+"): "Cash Accumulator",    # CFO + asset sales + financing inflows
    ("-", "-", "+"): "Growth Funded by Debt",  # Burning cash, raising capital for growth
    ("-", "+", "+"): "Distress Signal",     # Ops negative, selling assets + raising funds
    ("-", "-", "-"): "Pre-Revenue",         # All outflows — early stage or declining
    ("-", "+", "-"): "Asset Recycler",      # Selling assets to fund operations/debt
}


def classify_capital_allocation(
    operating_activity: float,
    investing_activity: float,
    financing_activity: float,
) -> tuple[str, str, str, str]:
    """
    Classify a company-year by capital allocation pattern.
    Returns (cfo_sign, cfi_sign, cff_sign, pattern_label).
    """
    cfo_s = _sign(operating_activity)
    cfi_s = _sign(investing_activity)
    cff_s = _sign(financing_activity)
    label = CAPITAL_ALLOCATION_PATTERNS.get((cfo_s, cfi_s, cff_s), "Unknown")
    return cfo_s, cfi_s, cff_s, label


def compute_capital_allocation_for_all(
    cashflow_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply capital allocation classifier to every row in the cashflow DataFrame.
    Returns a new DataFrame with columns:
      company_id, year, cfo_sign, cfi_sign, cff_sign, pattern_label
    """
    records = []
    for _, row in cashflow_df.iterrows():
        cfo_s, cfi_s, cff_s, label = classify_capital_allocation(
            row.get("operating_activity", 0),
            row.get("investing_activity", 0),
            row.get("financing_activity", 0),
        )
        records.append({
            "company_id":    row["company_id"],
            "year":          row["year"],
            "cfo_sign":      cfo_s,
            "cfi_sign":      cfi_s,
            "cff_sign":      cff_s,
            "pattern_label": label,
        })
    return pd.DataFrame(records)
