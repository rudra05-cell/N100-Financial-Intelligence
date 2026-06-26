"""
tests/dq/test_rules.py
Unit tests for all 16 Data Quality rules.
Each test crafts a DataFrame that deliberately violates one rule,
then confirms the validator detects it at the correct severity.

Run:  pytest tests/dq/test_rules.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/etl"))

import pandas as pd
import pytest
from validator import (
    _dq01_company_pk_uniqueness,
    _dq02_annual_pk_uniqueness,
    _dq03_fk_integrity,
    _dq04_bs_balance,
    _dq05_opm_crosscheck,
    _dq06_positive_sales,
    _dq07_year_format,
    _dq08_ticker_format,
    _dq09_net_cash_check,
    _dq10_nonneg_fixed_assets,
    _dq11_tax_rate_range,
    _dq12_dividend_payout_cap,
    _dq14_eps_sign,
    _dq16_coverage_check,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def companies(extra_rows=None):
    rows = [
        {"id": "TCS",  "company_name": "TCS"},
        {"id": "INFY", "company_name": "Infosys"},
    ]
    if extra_rows:
        rows += extra_rows
    return pd.DataFrame(rows)


def pl_row(**kwargs):
    base = {"company_id": "TCS", "year": "2023-03", "sales": 100000,
            "expenses": 80000, "operating_profit": 20000, "opm_percentage": 20.0,
            "interest": 0, "net_profit": 15000, "eps": 40.0,
            "tax_percentage": 25.0, "dividend_payout": 40.0}
    base.update(kwargs)
    return base


def bs_row(**kwargs):
    base = {"company_id": "TCS", "year": "2023-03",
            "total_assets": 1000, "total_liabilities": 1000,
            "fixed_assets": 200, "borrowings": 0,
            "equity_capital": 100, "reserves": 900}
    base.update(kwargs)
    return base


def cf_row(**kwargs):
    base = {"company_id": "TCS", "year": "2023-03",
            "operating_activity": 18000, "investing_activity": -5000,
            "financing_activity": -10000, "net_cash_flow": 3000}
    base.update(kwargs)
    return base


# ─── DQ-01 ────────────────────────────────────────────────────────────────────

def test_dq01_passes_no_duplicates():
    df = companies()
    failures = _dq01_company_pk_uniqueness(df)
    assert failures == []


def test_dq01_detects_duplicate_ticker():
    df = pd.DataFrame([{"id": "TCS"}, {"id": "TCS"}, {"id": "INFY"}])
    failures = _dq01_company_pk_uniqueness(df)
    assert len(failures) == 2
    assert all(f["severity"] == SEVERITY_CRITICAL for f in failures)
    assert all(f["rule_id"] == "DQ-01" for f in failures)


# ─── DQ-02 ────────────────────────────────────────────────────────────────────

def test_dq02_passes_unique_pairs():
    df = pd.DataFrame([pl_row(), pl_row(year="2022-03")])
    failures = _dq02_annual_pk_uniqueness(df, pd.DataFrame(), pd.DataFrame())
    assert failures == []


def test_dq02_detects_duplicate_year():
    df = pd.DataFrame([pl_row(), pl_row()])   # same company + year twice
    failures = _dq02_annual_pk_uniqueness(df, pd.DataFrame(), pd.DataFrame())
    assert len(failures) == 2
    assert failures[0]["severity"] == SEVERITY_CRITICAL


# ─── DQ-03 ────────────────────────────────────────────────────────────────────

def test_dq03_passes_valid_fks():
    co = companies()
    pl = pd.DataFrame([pl_row(company_id="TCS")])
    failures = _dq03_fk_integrity(co, pl, pd.DataFrame(), pd.DataFrame())
    assert failures == []


def test_dq03_detects_orphan_company():
    co = companies()
    pl = pd.DataFrame([pl_row(company_id="UNKNOWN_CO")])
    failures = _dq03_fk_integrity(co, pl, pd.DataFrame(), pd.DataFrame())
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_CRITICAL
    assert "UNKNOWN_CO" in failures[0]["issue"]


# ─── DQ-04 ────────────────────────────────────────────────────────────────────

def test_dq04_passes_balanced_sheet():
    df = pd.DataFrame([bs_row(total_assets=1000, total_liabilities=1000)])
    assert _dq04_bs_balance(df) == []


def test_dq04_triggers_warning():
    df = pd.DataFrame([bs_row(total_assets=1000, total_liabilities=1020)])
    failures = _dq04_bs_balance(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING
    assert failures[0]["rule_id"] == "DQ-04"


# ─── DQ-05 ────────────────────────────────────────────────────────────────────

def test_dq05_passes_matching_opm():
    # opm = 20000/100000 * 100 = 20.0 → matches source
    df = pd.DataFrame([pl_row(opm_percentage=20.0)])
    assert _dq05_opm_crosscheck(df) == []


def test_dq05_triggers_warning_large_diff():
    # source says 30%, computed = 20% → diff = 10% > 1%
    df = pd.DataFrame([pl_row(opm_percentage=30.0)])
    failures = _dq05_opm_crosscheck(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING


# ─── DQ-06 ────────────────────────────────────────────────────────────────────

def test_dq06_passes_positive_sales():
    df = pd.DataFrame([pl_row(sales=50000)])
    assert _dq06_positive_sales(df) == []


def test_dq06_triggers_zero_sales():
    df = pd.DataFrame([pl_row(sales=0)])
    failures = _dq06_positive_sales(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING


# ─── DQ-07 ────────────────────────────────────────────────────────────────────

def test_dq07_passes_normalised_year():
    df = pd.DataFrame([pl_row(year="2023-03")])
    assert _dq07_year_format(df, pd.DataFrame(), pd.DataFrame()) == []


def test_dq07_detects_parse_error():
    df = pd.DataFrame([pl_row(year="PARSE_ERROR")])
    failures = _dq07_year_format(df, pd.DataFrame(), pd.DataFrame())
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_CRITICAL


# ─── DQ-08 ────────────────────────────────────────────────────────────────────

def test_dq08_passes_valid_ticker():
    co = pd.DataFrame([{"id": "TCS"}])
    assert _dq08_ticker_format(co, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()) == []


def test_dq08_detects_invalid_length():
    co = pd.DataFrame([{"id": "A"}])   # single char — too short
    failures = _dq08_ticker_format(co, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_CRITICAL


# ─── DQ-09 ────────────────────────────────────────────────────────────────────

def test_dq09_passes_matching_cash():
    # 18000 + (-5000) + (-10000) = 3000 → matches
    df = pd.DataFrame([cf_row()])
    assert _dq09_net_cash_check(df) == []


def test_dq09_triggers_large_mismatch():
    # computed = 3000, source says 5000 → diff = 2000 > 10
    df = pd.DataFrame([cf_row(net_cash_flow=5000)])
    failures = _dq09_net_cash_check(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING


# ─── DQ-10 ────────────────────────────────────────────────────────────────────

def test_dq10_passes_nonneg_assets():
    df = pd.DataFrame([bs_row(fixed_assets=200)])
    assert _dq10_nonneg_fixed_assets(df) == []


def test_dq10_triggers_negative_assets():
    df = pd.DataFrame([bs_row(fixed_assets=-50)])
    failures = _dq10_nonneg_fixed_assets(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING


# ─── DQ-11 ────────────────────────────────────────────────────────────────────

def test_dq11_passes_normal_tax():
    df = pd.DataFrame([pl_row(tax_percentage=25.0)])
    assert _dq11_tax_rate_range(df) == []


def test_dq11_triggers_out_of_range():
    df = pd.DataFrame([pl_row(tax_percentage=75.0)])   # > 60
    failures = _dq11_tax_rate_range(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING


# ─── DQ-12 ────────────────────────────────────────────────────────────────────

def test_dq12_passes_normal_payout():
    df = pd.DataFrame([pl_row(dividend_payout=45.0)])
    assert _dq12_dividend_payout_cap(df) == []


def test_dq12_triggers_excessive_payout():
    df = pd.DataFrame([pl_row(dividend_payout=250.0)])   # > 200
    failures = _dq12_dividend_payout_cap(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING


# ─── DQ-14 ────────────────────────────────────────────────────────────────────

def test_dq14_passes_positive_eps_with_profit():
    df = pd.DataFrame([pl_row(net_profit=15000, eps=40.0)])
    assert _dq14_eps_sign(df) == []


def test_dq14_triggers_zero_eps_with_profit():
    df = pd.DataFrame([pl_row(net_profit=15000, eps=-1.0)])
    failures = _dq14_eps_sign(df)
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING


# ─── DQ-16 ────────────────────────────────────────────────────────────────────

def test_dq16_passes_sufficient_coverage():
    rows = [pl_row(year=f"201{i}-03") for i in range(5)]
    df = pd.DataFrame(rows)
    failures = _dq16_coverage_check(df, pd.DataFrame(), pd.DataFrame())
    assert failures == []


def test_dq16_triggers_insufficient_coverage():
    rows = [pl_row(year=f"202{i}-03") for i in range(3)]   # only 3 years
    df = pd.DataFrame(rows)
    failures = _dq16_coverage_check(df, pd.DataFrame(), pd.DataFrame())
    assert len(failures) == 1
    assert failures[0]["severity"] == SEVERITY_WARNING
