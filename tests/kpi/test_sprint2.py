"""
tests/kpi/test_sprint2.py
Sprint 2 unit tests that import the actual src/analytics modules.
Covers: ratios.py, cagr.py, cashflow_kpis.py.

Run:  pytest tests/kpi/test_sprint2.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/analytics"))

import pytest
import pandas as pd

from ratios import (
    net_profit_margin, operating_profit_margin, return_on_equity,
    return_on_capital_employed, return_on_assets, debt_to_equity,
    interest_coverage_ratio, net_debt, asset_turnover,
)
from cagr import cagr, compute_all_cagrs_for_company
from cashflow_kpis import (
    free_cash_flow, capex_intensity, fcf_conversion_rate,
    classify_capital_allocation, cfo_quality_score,
)


# ══════════════════════════════════════════════════════════════════════════════
# ratios.py — Profitability (Day 08)
# ══════════════════════════════════════════════════════════════════════════════

class TestProfitabilityRatios:

    def test_npm_normal(self):
        assert net_profit_margin(15000, 100000) == pytest.approx(15.0, abs=0.01)

    def test_npm_zero_sales_returns_none(self):
        assert net_profit_margin(1000, 0) is None

    def test_npm_negative_profit_allowed(self):
        assert net_profit_margin(-5000, 100000) == pytest.approx(-5.0, abs=0.01)

    def test_opm_normal(self):
        assert operating_profit_margin(20000, 100000) == pytest.approx(20.0, abs=0.01)

    def test_opm_zero_sales_returns_none(self):
        assert operating_profit_margin(5000, 0) is None

    def test_roe_positive_equity(self):
        assert return_on_equity(100, 200, 300) == pytest.approx(20.0, abs=0.01)

    def test_roe_negative_equity_returns_none(self):
        assert return_on_equity(100, 10, -100) is None

    def test_roe_zero_equity_returns_none(self):
        assert return_on_equity(100, 0, 0) is None

    def test_roce_normal(self):
        # EBIT = 20000 - 5000 = 15000; CE = 100 + 900 + 0 = 1000 → 1500%
        result = return_on_capital_employed(20000, 5000, 100, 900, 0)
        assert result == pytest.approx(1500.0, abs=0.1)

    def test_roa_normal(self):
        assert return_on_assets(5000, 100000) == pytest.approx(5.0, abs=0.01)

    def test_roa_zero_assets_returns_none(self):
        assert return_on_assets(5000, 0) is None


# ══════════════════════════════════════════════════════════════════════════════
# ratios.py — Leverage (Day 09)
# ══════════════════════════════════════════════════════════════════════════════

class TestLeverageRatios:

    def test_de_zero_debt_returns_zero(self):
        ratio, flag = debt_to_equity(0, 100, 400)
        assert ratio == 0.0
        assert flag is False

    def test_de_normal(self):
        ratio, flag = debt_to_equity(250, 100, 400)
        assert ratio == pytest.approx(0.5, abs=0.01)
        assert flag is False

    def test_de_high_leverage_non_financial_flags(self):
        ratio, flag = debt_to_equity(3000, 100, 400, broad_sector="Energy")
        assert ratio > 5
        assert flag is True

    def test_de_high_leverage_financial_no_flag(self):
        ratio, flag = debt_to_equity(3000, 100, 400, broad_sector="Financials")
        assert ratio > 5
        assert flag is False   # banks suppressed

    def test_de_negative_equity_returns_none(self):
        ratio, flag = debt_to_equity(100, 10, -50)
        assert ratio is None

    def test_icr_debt_free_returns_none_and_label(self):
        val, label = interest_coverage_ratio(10000, 500, 0)
        assert val is None
        assert label == "Debt Free"

    def test_icr_normal_safe(self):
        val, label = interest_coverage_ratio(10000, 500, 2000)
        assert val == pytest.approx(5.25, abs=0.01)
        assert label == "Safe"

    def test_icr_below_1_5_at_risk(self):
        val, label = interest_coverage_ratio(1000, 0, 2000)
        assert val == pytest.approx(0.5, abs=0.01)
        assert label == "At Risk"

    def test_net_debt_with_debt(self):
        assert net_debt(1000, 200) == pytest.approx(800.0, abs=0.01)

    def test_net_debt_cash_positive(self):
        # investments > borrowings → net cash positive
        assert net_debt(200, 500) == pytest.approx(-300.0, abs=0.01)

    def test_asset_turnover_normal(self):
        assert asset_turnover(200000, 100000) == pytest.approx(2.0, abs=0.01)

    def test_asset_turnover_zero_assets_returns_none(self):
        assert asset_turnover(200000, 0) is None


# ══════════════════════════════════════════════════════════════════════════════
# cagr.py (Day 10)
# ══════════════════════════════════════════════════════════════════════════════

class TestCAGR:

    def test_cagr_normal(self):
        val, flag = cagr(100, 161.05, 5)
        assert flag is None
        assert val == pytest.approx(10.0, abs=0.1)

    def test_cagr_turnaround(self):
        val, flag = cagr(-100, 200, 5)
        assert val is None
        assert flag == "TURNAROUND"

    def test_cagr_decline_to_loss(self):
        val, flag = cagr(100, -50, 5)
        assert val is None
        assert flag == "DECLINE_TO_LOSS"

    def test_cagr_both_negative(self):
        val, flag = cagr(-100, -200, 5)
        assert val is None
        assert flag == "BOTH_NEGATIVE"

    def test_cagr_zero_base(self):
        val, flag = cagr(0, 100, 5)
        assert val is None
        assert flag == "ZERO_BASE"

    def test_cagr_insufficient_years(self):
        val, flag = cagr(100, 200, 2)
        assert val is None
        assert flag == "INSUFFICIENT"

    def test_cagr_exactly_3yr(self):
        # 3 years is minimum valid
        val, flag = cagr(100, 133.1, 3)
        assert flag is None
        assert val == pytest.approx(10.0, abs=0.2)

    def test_compute_all_cagrs_returns_expected_columns(self):
        pl = pd.DataFrame({
            "company_id":  ["TCS"] * 8,
            "year":        [f"201{i}-03" for i in range(8)],
            "sales":       [50000 * (1.1**i) for i in range(8)],
            "net_profit":  [8000  * (1.1**i) for i in range(8)],
            "eps":         [20    * (1.1**i) for i in range(8)],
        })
        result = compute_all_cagrs_for_company(pl)
        assert "revenue_cagr_3yr"   in result.columns
        assert "revenue_cagr_5yr"   in result.columns
        assert "pat_cagr_5yr"       in result.columns
        assert "eps_cagr_5yr"       in result.columns
        # Last row should have 5yr CAGR computable
        last = result.iloc[-1]
        assert last["revenue_cagr_5yr"] is not None
        assert last["revenue_cagr_5yr_flag"] is None


# ══════════════════════════════════════════════════════════════════════════════
# cashflow_kpis.py (Day 11)
# ══════════════════════════════════════════════════════════════════════════════

class TestCashFlowKPIs:

    def test_fcf_positive(self):
        assert free_cash_flow(38000, -12000) == 26000

    def test_fcf_negative(self):
        assert free_cash_flow(-5000, -10000) == -15000

    def test_fcf_none_investing(self):
        assert free_cash_flow(10000, None) == 10000

    def test_capex_intensity_asset_light(self):
        pct, label = capex_intensity(-2000, 100000)
        assert pct == pytest.approx(2.0, abs=0.01)
        assert label == "Asset Light"

    def test_capex_intensity_moderate(self):
        pct, label = capex_intensity(-5000, 100000)
        assert label == "Moderate"

    def test_capex_intensity_capital_intensive(self):
        pct, label = capex_intensity(-15000, 100000)
        assert label == "Capital Intensive"

    def test_capex_intensity_zero_sales_returns_none(self):
        pct, label = capex_intensity(-5000, 0)
        assert pct is None

    def test_fcf_conversion_normal(self):
        result = fcf_conversion_rate(26000, 40000)
        assert result == pytest.approx(65.0, abs=0.1)

    def test_fcf_conversion_zero_opprofit_returns_none(self):
        assert fcf_conversion_rate(5000, 0) is None

    def test_capital_allocation_reinvestor(self):
        cfo_s, cfi_s, cff_s, label = classify_capital_allocation(38000, -12000, -25000)
        assert cfo_s == "+"
        assert cfi_s == "-"
        assert cff_s == "-"
        assert label == "Reinvestor"

    def test_capital_allocation_distress(self):
        _, _, _, label = classify_capital_allocation(-5000, 3000, 10000)
        assert label == "Distress Signal"

    def test_capital_allocation_growth_by_debt(self):
        _, _, _, label = classify_capital_allocation(-5000, -8000, 15000)
        assert label == "Growth Funded by Debt"

    def test_cfo_quality_high(self):
        ratio, label = cfo_quality_score([38000, 40000, 42000], [30000, 32000, 34000])
        assert ratio > 1.0
        assert label == "High Quality Earnings"

    def test_cfo_quality_accrual_risk(self):
        ratio, label = cfo_quality_score([5000, 4000, 3000], [30000, 32000, 34000])
        assert label == "Accrual Risk"
