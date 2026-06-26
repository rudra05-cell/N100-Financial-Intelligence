"""
src/analytics/ratios.py
Day 08–09 — Profitability, Leverage & Efficiency Ratios.
All functions are pure: they take scalar inputs and return a scalar result.
None is returned (not NaN, not 0) whenever a denominator is zero or invalid.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Financial sector set — used to suppress D/E flag & adjust ROCE ───────────
FINANCIAL_SECTORS = {"Financials"}


# ══════════════════════════════════════════════════════════════════════════════
# PROFITABILITY RATIOS  (Day 08)
# ══════════════════════════════════════════════════════════════════════════════

def net_profit_margin(net_profit: float, sales: float) -> Optional[float]:
    """NPM = net_profit / sales × 100. None if sales = 0."""
    if not sales:
        return None
    return round(net_profit / sales * 100, 4)


def operating_profit_margin(operating_profit: float, sales: float) -> Optional[float]:
    """OPM = operating_profit / sales × 100. None if sales = 0."""
    if not sales:
        return None
    return round(operating_profit / sales * 100, 4)


def opm_crosscheck(
    opm_source: float, operating_profit: float, sales: float, tolerance: float = 1.0
) -> Optional[float]:
    """
    Return the difference between source OPM% and computed OPM%.
    Returns None if cannot compute. Log a warning if diff > tolerance.
    Used in ratio_edge_cases.log.
    """
    if not sales:
        return None
    computed = operating_profit / sales * 100
    diff = abs((opm_source or 0) - computed)
    if diff > tolerance:
        logger.debug("OPM mismatch: source=%.2f computed=%.2f diff=%.2f", opm_source, computed, diff)
    return round(diff, 4)


def return_on_equity(
    net_profit: float, equity_capital: float, reserves: float
) -> Optional[float]:
    """ROE = net_profit / (equity_capital + reserves) × 100. None if equity ≤ 0."""
    equity = (equity_capital or 0) + (reserves or 0)
    if equity <= 0:
        return None
    return round(net_profit / equity * 100, 4)


def return_on_capital_employed(
    operating_profit: float,
    depreciation: float,
    equity_capital: float,
    reserves: float,
    borrowings: float,
) -> Optional[float]:
    """
    ROCE = EBIT / (equity + reserves + borrowings) × 100.
    EBIT = operating_profit − depreciation.
    None if capital_employed ≤ 0.
    """
    ebit = (operating_profit or 0) - (depreciation or 0)
    capital_employed = (equity_capital or 0) + (reserves or 0) + (borrowings or 0)
    if capital_employed <= 0:
        return None
    return round(ebit / capital_employed * 100, 4)


def return_on_assets(net_profit: float, total_assets: float) -> Optional[float]:
    """ROA = net_profit / total_assets × 100. None if total_assets = 0."""
    if not total_assets:
        return None
    return round(net_profit / total_assets * 100, 4)


# ══════════════════════════════════════════════════════════════════════════════
# LEVERAGE RATIOS  (Day 09)
# ══════════════════════════════════════════════════════════════════════════════

def debt_to_equity(
    borrowings: float,
    equity_capital: float,
    reserves: float,
    broad_sector: str = "",
) -> tuple[Optional[float], bool]:
    """
    D/E = borrowings / (equity_capital + reserves).
    Returns (ratio, high_leverage_flag).
    - ratio = 0 if borrowings = 0 (debt-free)
    - ratio = None if equity ≤ 0
    - high_leverage_flag = True if D/E > 5 AND sector is NOT Financials
    """
    if not borrowings or borrowings == 0:
        return 0.0, False
    equity = (equity_capital or 0) + (reserves or 0)
    if equity <= 0:
        return None, False
    ratio = round(borrowings / equity, 4)
    is_financial = broad_sector in FINANCIAL_SECTORS
    high_flag = (ratio > 5) and not is_financial
    return ratio, high_flag


def interest_coverage_ratio(
    operating_profit: float,
    other_income: float,
    interest: float,
) -> tuple[Optional[float], str]:
    """
    ICR = (operating_profit + other_income) / interest.
    Returns (value, label):
    - (None, 'Debt Free') if interest = 0
    - (float, 'At Risk')  if ICR < 1.5
    - (float, 'Safe')     if ICR >= 1.5
    """
    if not interest or interest == 0:
        return None, "Debt Free"
    icr = (operating_profit + (other_income or 0)) / interest
    label = "At Risk" if icr < 1.5 else "Safe"
    return round(icr, 4), label


def net_debt(borrowings: float, investments: float) -> float:
    """Net Debt = borrowings − investments (investments as liquid asset proxy)."""
    return round((borrowings or 0) - (investments or 0), 4)


def asset_turnover(sales: float, total_assets: float) -> Optional[float]:
    """Asset Turnover = sales / total_assets. None if total_assets = 0."""
    if not total_assets:
        return None
    return round(sales / total_assets, 4)


def book_value_per_share(
    equity_capital: float, reserves: float, face_value: float
) -> Optional[float]:
    """
    BVPS = (equity_capital + reserves) / shares_outstanding.
    shares_outstanding = equity_capital / face_value (in crores × 10M shares per crore).
    Returns None if face_value = 0.
    """
    if not face_value or face_value == 0:
        return None
    equity = (equity_capital or 0) + (reserves or 0)
    # equity_capital in ₹ Cr, face_value in ₹
    # shares = (equity_capital * 10_000_000) / face_value  →  in units
    # BVPS = equity (Cr) * 10_000_000 / shares = face_value * equity / equity_capital
    if not equity_capital or equity_capital == 0:
        return None
    shares = (equity_capital * 1e7) / face_value        # total shares
    bvps = (equity * 1e7) / shares                      # ₹ per share
    return round(bvps, 4)
