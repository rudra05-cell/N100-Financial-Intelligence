"""
tests/kpi/test_ratios.py
Unit tests for KPI formula logic used by the Ratio Engine (Sprint 2).
Tests are written NOW (Sprint 1) to define expected behaviour before implementation.

Run:  pytest tests/kpi/test_ratios.py -v
"""

import pytest


# ─── Pure formula functions (inline — no import needed until ratios.py exists)
# These replicate the exact logic the Ratio Engine must implement.
# Sprint 2 will move these to src/analytics/ratios.py.
# ─────────────────────────────────────────────────────────────────────────────

def compute_roe(net_profit, equity_capital, reserves):
    """ROE = net_profit / (equity + reserves) * 100. None if equity <= 0."""
    equity = (equity_capital or 0) + (reserves or 0)
    if equity <= 0:
        return None
    return round(net_profit / equity * 100, 4)


def compute_de(borrowings, equity_capital, reserves):
    """D/E = borrowings / (equity + reserves). 0 if debt-free."""
    equity = (equity_capital or 0) + (reserves or 0)
    if equity <= 0:
        return None
    return round(borrowings / equity, 4)


def compute_icr(operating_profit, other_income, interest):
    """ICR = (op_profit + other_income) / interest. None if interest = 0."""
    if not interest or interest == 0:
        return None   # display as 'Debt Free'
    return round((operating_profit + (other_income or 0)) / interest, 4)


def compute_npm(net_profit, sales):
    """Net Profit Margin = net_profit / sales * 100. None if sales = 0."""
    if not sales or sales == 0:
        return None
    return round(net_profit / sales * 100, 4)


def compute_cagr(start_val, end_val, n_years):
    """
    CAGR = ((end/start)^(1/n) - 1) * 100.
    Returns (value, flag):
      - (float, None)          → normal
      - (None, 'TURNAROUND')   → base < 0, end > 0
      - (None, 'DECLINE_TO_LOSS') → base > 0, end < 0
      - (None, 'BOTH_NEGATIVE')   → both < 0
      - (None, 'ZERO_BASE')       → base = 0
      - (None, 'INSUFFICIENT')    → n_years < 3
    """
    if n_years < 3:
        return None, "INSUFFICIENT"
    if start_val == 0:
        return None, "ZERO_BASE"
    if start_val < 0 and end_val > 0:
        return None, "TURNAROUND"
    if start_val > 0 and end_val < 0:
        return None, "DECLINE_TO_LOSS"
    if start_val < 0 and end_val < 0:
        return None, "BOTH_NEGATIVE"
    result = ((end_val / start_val) ** (1 / n_years) - 1) * 100
    return round(result, 4), None


def compute_fcf(operating_activity, investing_activity):
    """FCF = CFO + CFI."""
    return (operating_activity or 0) + (investing_activity or 0)


# ─── ROE tests ────────────────────────────────────────────────────────────────

def test_roe_positive_equity():
    result = compute_roe(net_profit=100, equity_capital=200, reserves=300)
    assert result == pytest.approx(20.0, abs=0.01)


def test_roe_negative_equity_returns_none():
    result = compute_roe(net_profit=100, equity_capital=10, reserves=-100)
    assert result is None


def test_roe_zero_equity_returns_none():
    result = compute_roe(net_profit=100, equity_capital=0, reserves=0)
    assert result is None


def test_roe_negative_profit_allowed():
    result = compute_roe(net_profit=-50, equity_capital=200, reserves=300)
    assert result == pytest.approx(-10.0, abs=0.01)


# ─── D/E tests ────────────────────────────────────────────────────────────────

def test_de_zero_debt_is_zero():
    result = compute_de(borrowings=0, equity_capital=100, reserves=400)
    assert result == 0.0


def test_de_with_debt():
    result = compute_de(borrowings=250, equity_capital=100, reserves=400)
    assert result == pytest.approx(0.5, abs=0.01)


def test_de_negative_equity_returns_none():
    result = compute_de(borrowings=100, equity_capital=10, reserves=-50)
    assert result is None


# ─── ICR tests ────────────────────────────────────────────────────────────────

def test_icr_debt_free_returns_none():
    result = compute_icr(operating_profit=10000, other_income=500, interest=0)
    assert result is None


def test_icr_normal():
    result = compute_icr(operating_profit=10000, other_income=500, interest=2000)
    assert result == pytest.approx(5.25, abs=0.01)


def test_icr_below_one_dangerous():
    result = compute_icr(operating_profit=1000, other_income=0, interest=2000)
    assert result == pytest.approx(0.5, abs=0.01)
    assert result < 1.0


# ─── NPM tests ────────────────────────────────────────────────────────────────

def test_npm_normal():
    result = compute_npm(net_profit=15000, sales=100000)
    assert result == pytest.approx(15.0, abs=0.01)


def test_npm_zero_sales_returns_none():
    result = compute_npm(net_profit=1000, sales=0)
    assert result is None


def test_npm_negative_allowed():
    result = compute_npm(net_profit=-5000, sales=100000)
    assert result == pytest.approx(-5.0, abs=0.01)


# ─── CAGR tests ───────────────────────────────────────────────────────────────

def test_cagr_normal():
    # 100 → 161.05 over 5 years ≈ 10%
    val, flag = compute_cagr(start_val=100, end_val=161.05, n_years=5)
    assert flag is None
    assert val == pytest.approx(10.0, abs=0.1)


def test_cagr_turnaround():
    val, flag = compute_cagr(start_val=-100, end_val=200, n_years=5)
    assert val is None
    assert flag == "TURNAROUND"


def test_cagr_decline_to_loss():
    val, flag = compute_cagr(start_val=100, end_val=-50, n_years=5)
    assert val is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_both_negative():
    val, flag = compute_cagr(start_val=-100, end_val=-200, n_years=5)
    assert val is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_zero_base():
    val, flag = compute_cagr(start_val=0, end_val=100, n_years=5)
    assert val is None
    assert flag == "ZERO_BASE"


def test_cagr_insufficient_history():
    val, flag = compute_cagr(start_val=100, end_val=200, n_years=2)
    assert val is None
    assert flag == "INSUFFICIENT"


# ─── FCF tests ────────────────────────────────────────────────────────────────

def test_fcf_positive_generating_cash():
    result = compute_fcf(operating_activity=38000, investing_activity=-12000)
    assert result == 26000


def test_fcf_negative_burning_cash():
    result = compute_fcf(operating_activity=-5000, investing_activity=-10000)
    assert result == -15000


def test_fcf_handles_none():
    result = compute_fcf(operating_activity=10000, investing_activity=None)
    assert result == 10000
