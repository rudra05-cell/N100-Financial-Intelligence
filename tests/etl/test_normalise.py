"""
tests/etl/test_normalise.py
35+ unit tests for normalize_year() and normalize_ticker().
Run:  pytest tests/etl/test_normalise.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/etl"))

import pytest
from normaliser import normalize_year, normalize_ticker, is_valid_year, is_valid_ticker


# ══════════════════════════════════════════════════════════════════════════════
# normalize_year() — 22 test cases
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeYear:

    # ── Standard format ───────────────────────────────────────────
    def test_mar23_standard(self):
        assert normalize_year("Mar-23") == "2023-03"

    def test_mar22_standard(self):
        assert normalize_year("Mar-22") == "2022-03"

    def test_mar24_standard(self):
        assert normalize_year("Mar-24") == "2024-03"

    # ── Space separator ───────────────────────────────────────────
    def test_mar_space_23(self):
        assert normalize_year("Mar 23") == "2023-03"

    def test_jun_space_23(self):
        assert normalize_year("Jun 23") == "2023-06"

    # ── Full month name ───────────────────────────────────────────
    def test_march_2023_full(self):
        assert normalize_year("March-2023") == "2023-03"

    def test_december_2022_full(self):
        assert normalize_year("December-2022") == "2022-12"

    # ── December year-end (NESTLEIND style) ───────────────────────
    def test_dec22(self):
        assert normalize_year("Dec-22") == "2022-12"

    def test_dec21(self):
        assert normalize_year("Dec-21") == "2021-12"

    # ── June year-end (some banks) ────────────────────────────────
    def test_jun23(self):
        assert normalize_year("Jun-23") == "2023-06"

    # ── FY prefix ─────────────────────────────────────────────────
    def test_fy23(self):
        assert normalize_year("FY23") == "2023-03"

    def test_fy24(self):
        assert normalize_year("FY24") == "2024-03"

    def test_fy2023_long(self):
        assert normalize_year("FY2023") == "2023-03"

    # ── Integer year ──────────────────────────────────────────────
    def test_integer_year_2023(self):
        assert normalize_year(2023) == "2023-03"

    def test_integer_year_2020(self):
        assert normalize_year(2020) == "2020-03"

    # ── Already normalised ────────────────────────────────────────
    def test_already_normalised(self):
        assert normalize_year("2023-03") == "2023-03"

    def test_already_normalised_dec(self):
        assert normalize_year("2022-12") == "2022-12"

    # ── Case insensitive ─────────────────────────────────────────
    def test_lowercase_mar(self):
        assert normalize_year("mar-23") == "2023-03"

    def test_uppercase_MAR(self):
        assert normalize_year("MAR-23") == "2023-03"

    # ── None and garbage ─────────────────────────────────────────
    def test_none_input(self):
        assert normalize_year(None) == "PARSE_ERROR"

    def test_garbage_string(self):
        assert normalize_year("xyz") == "PARSE_ERROR"

    def test_empty_string(self):
        assert normalize_year("") == "PARSE_ERROR"


# ══════════════════════════════════════════════════════════════════════════════
# normalize_ticker() — 15 test cases
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeTicker:

    # ── Standard tickers ──────────────────────────────────────────
    def test_tcs_uppercase(self):
        assert normalize_ticker("TCS") == "TCS"

    def test_tcs_lowercase(self):
        assert normalize_ticker("tcs") == "TCS"

    def test_tcs_mixed(self):
        assert normalize_ticker("Tcs") == "TCS"

    # ── Whitespace stripping ──────────────────────────────────────
    def test_strip_leading_space(self):
        assert normalize_ticker(" TCS") == "TCS"

    def test_strip_trailing_space(self):
        assert normalize_ticker("TCS ") == "TCS"

    def test_strip_both_spaces(self):
        assert normalize_ticker("  tcs  ") == "TCS"

    # ── Special characters preserved ─────────────────────────────
    def test_hyphen_preserved(self):
        assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

    def test_hyphen_lowercase_preserved(self):
        assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"

    def test_ampersand_preserved(self):
        assert normalize_ticker("M&M") == "M&M"

    def test_ampersand_lowercase(self):
        assert normalize_ticker("m&m") == "M&M"

    # ── Edge cases ────────────────────────────────────────────────
    def test_two_char_minimum(self):
        # 2 chars is valid
        assert normalize_ticker("AB") == "AB"

    def test_twelve_char_maximum(self):
        # 12 chars is valid
        assert normalize_ticker("ABCDEFGHIJKL") == "ABCDEFGHIJKL"

    # ── Invalid cases ────────────────────────────────────────────
    def test_too_short_one_char(self):
        assert normalize_ticker("A") == "INVALID"

    def test_empty_string(self):
        assert normalize_ticker("") == "INVALID"

    def test_none_input(self):
        assert normalize_ticker(None) == "INVALID"


# ══════════════════════════════════════════════════════════════════════════════
# is_valid_year() and is_valid_ticker() helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestValidationHelpers:

    def test_valid_year_true(self):
        assert is_valid_year("2023-03") is True

    def test_parse_error_is_invalid(self):
        assert is_valid_year("PARSE_ERROR") is False

    def test_valid_ticker_true(self):
        assert is_valid_ticker("TCS") is True

    def test_invalid_ticker_false(self):
        assert is_valid_ticker("INVALID") is False
