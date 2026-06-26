"""
tests/conftest.py
Shared pytest fixtures available to all test files.
"""

import sys
import os

# Make src modules importable from tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/etl"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/analytics"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pytest
import pandas as pd


@pytest.fixture
def sample_companies() -> pd.DataFrame:
    """Minimal companies DataFrame for testing."""
    return pd.DataFrame({
        "id":           ["TCS", "INFY", "HDFCBANK"],
        "company_name": ["Tata Consultancy Services", "Infosys", "HDFC Bank"],
        "face_value":   [1, 5, 1],
        "book_value":   [157.4, 145.0, 220.0],
        "roe_percentage":[48.0, 30.0, 16.0],
        "roce_percentage":[64.3, 40.0, 18.0],
    })


@pytest.fixture
def sample_profitandloss() -> pd.DataFrame:
    """Minimal P&L DataFrame for testing."""
    return pd.DataFrame({
        "company_id":       ["TCS", "TCS",   "INFY"],
        "year":             ["2023-03", "2022-03", "2023-03"],
        "sales":            [225458,  191754,  146767],
        "expenses":         [176924,  147854,  118765],
        "operating_profit": [48534,   43900,   28002],
        "opm_percentage":   [21.5,    22.9,    19.1],
        "other_income":     [3800,    3200,    2500],
        "interest":         [0,       0,       0],
        "depreciation":     [5800,    5400,    5100],
        "profit_before_tax":[46534,   41700,   25402],
        "tax_percentage":   [25.0,    25.5,    24.5],
        "net_profit":       [34990,   31098,   19183],
        "eps":              [95.3,    84.6,    45.2],
        "dividend_payout":  [45.0,    40.0,    35.0],
    })


@pytest.fixture
def sample_balancesheet() -> pd.DataFrame:
    """Minimal Balance Sheet DataFrame for testing."""
    return pd.DataFrame({
        "company_id":       ["TCS", "HDFCBANK"],
        "year":             ["2023-03", "2023-03"],
        "equity_capital":   [366,     558],
        "reserves":         [53000,   285000],
        "borrowings":       [0,       1450000],
        "other_liabilities":[30000,   200000],
        "total_liabilities":[83366,   1936558],
        "fixed_assets":     [12000,   5500],
        "cwip":             [500,     100],
        "investments":      [20000,   350000],
        "other_asset":      [50866,   1580958],
        "total_assets":     [83366,   1936558],
    })


@pytest.fixture
def sample_cashflow() -> pd.DataFrame:
    """Minimal Cash Flow DataFrame for testing."""
    return pd.DataFrame({
        "company_id":          ["TCS",  "INFY"],
        "year":                ["2023-03","2023-03"],
        "operating_activity":  [38000,   22000],
        "investing_activity":  [-12000,  -8000],
        "financing_activity":  [-25000,  -14000],
        "net_cash_flow":       [1000,    0],
    })
