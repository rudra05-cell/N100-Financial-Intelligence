"""
src/etl/normaliser.py
Normalisation utilities for year labels and company tickers.
Every raw value from the Excel files passes through these functions
before touching the database.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# MONTH MAP  — covers all abbreviated and full month names seen in source data
# ──────────────────────────────────────────────────────────────────────────────
MONTH_MAP: dict[str, str] = {
    "jan": "01", "january":  "01",
    "feb": "02", "february": "02",
    "mar": "03", "march":    "03",
    "apr": "04", "april":    "04",
    "may": "05",
    "jun": "06", "june":     "06",
    "jul": "07", "july":     "07",
    "aug": "08", "august":   "08",
    "sep": "09", "september":"09",
    "oct": "10", "october":  "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}


def normalize_year(raw: object) -> str:
    """
    Convert any raw year label from the Excel files into the standard
    format  YYYY-MM  (e.g. 'Mar-23' → '2023-03').

    Handles:
        Mar-23          → 2023-03   (most common — monthly P&L label)
        Mar 23          → 2023-03   (space separator)
        March-2023      → 2023-03   (full month name)
        2023            → 2023-03   (integer year — assume March FY close)
        FY23            → 2023-03   (FY prefix)
        FY2023          → 2023-03
        Dec-22          → 2022-12   (December year-end e.g. NESTLEIND)
        Jun-23          → 2023-06   (June year-end e.g. some banks)
        2023-03         → 2023-03   (already normalised — pass through)
        garbage         → PARSE_ERROR

    Returns:
        Normalised string 'YYYY-MM', or 'PARSE_ERROR' if unparseable.
    """
    if raw is None:
        return "PARSE_ERROR"

    value = str(raw).strip()

    # 0. Explicit exclusions — not a financial year label, drop these rows
    #    TTM = Trailing Twelve Months (not a discrete year)
    #    "Mar 2016 9m" = 9-month partial period
    #    "Mar 2023 15" = 15-month period
    upper_val = value.upper()
    if upper_val == "TTM":
        return "PARSE_ERROR"
    if re.search(r"\d+m\b", value, re.IGNORECASE):   # e.g. "Mar 2016 9m"
        return "PARSE_ERROR"
    if re.search(r"^\w+\s+\d{4}\s+\d+$", value):     # e.g. "Mar 2023 15"
        return "PARSE_ERROR"

    # 1. Already in correct format YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", value):
        return value

    # 2. Pure 4-digit year  e.g. 2023  →  2023-03
    if re.match(r"^\d{4}$", value):
        return f"{value}-03"

    # 3. FY23 or FY2023
    fy_match = re.match(r"^FY\s*(\d{2,4})$", value, re.IGNORECASE)
    if fy_match:
        yr = fy_match.group(1)
        full_year = _expand_year(yr)
        return f"{full_year}-03"

    # 4. Mon-YY  /  Mon-YYYY  /  Mon YY  /  Mon YYYY  /  Month-YYYY
    #    e.g. Mar-23, Mar-2023, Mar 23, March-2023
    mon_yr = re.match(
        r"^([A-Za-z]+)[\s\-](\d{2,4})$", value
    )
    if mon_yr:
        month_str = mon_yr.group(1).lower()
        year_str  = mon_yr.group(2)
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            full_year = _expand_year(year_str)
            return f"{full_year}-{month_num}"

    # 5. YYYY-Mon  e.g. 2023-Mar
    yr_mon = re.match(r"^(\d{4})[\s\-]([A-Za-z]+)$", value)
    if yr_mon:
        year_str  = yr_mon.group(1)
        month_str = yr_mon.group(2).lower()
        month_num = MONTH_MAP.get(month_str)
        if month_num:
            return f"{year_str}-{month_num}"

    # 6. Pure 2-digit year  e.g. 23  →  2023-03
    if re.match(r"^\d{2}$", value):
        full_year = _expand_year(value)
        return f"{full_year}-03"

    logger.warning("normalize_year: unparseable value '%s'", raw)
    return "PARSE_ERROR"


def _expand_year(yr_str: str) -> str:
    """
    Convert 2-digit year to 4-digit year.
    00–29 → 2000–2029
    30–99 → 1930–1999  (no Nifty 100 data that old, but safe)
    4-digit years pass through unchanged.
    """
    yr = yr_str.strip()
    if len(yr) == 4:
        return yr
    n = int(yr)
    return f"20{yr:0>2}" if n < 30 else f"19{yr:0>2}"


def normalize_ticker(raw: object) -> str:
    """
    Normalise an NSE ticker / company_id value.

    Rules:
        - Strip leading/trailing whitespace
        - Convert to UPPERCASE
        - Preserve hyphens (BAJAJ-AUTO) and ampersands (M&M)
        - Length must be 2–12 characters after normalisation
        - Return 'INVALID' if out of range or empty

    Examples:
        'TCS'       → 'TCS'
        ' tcs '     → 'TCS'
        'bajaj-auto'→ 'BAJAJ-AUTO'
        'm&m'       → 'M&M'
        ''          → 'INVALID'
        'A'         → 'INVALID'  (too short)
    """
    if raw is None:
        return "INVALID"

    cleaned = str(raw).strip().upper()

    if len(cleaned) < 2 or len(cleaned) > 12:
        logger.warning("normalize_ticker: length out of range for '%s'", raw)
        return "INVALID"

    return cleaned


def is_valid_year(year_str: str) -> bool:
    """Return True if year_str matches YYYY-MM and was not a parse error."""
    return bool(re.match(r"^\d{4}-\d{2}$", year_str)) and year_str != "PARSE_ERROR"


def is_valid_ticker(ticker: str) -> bool:
    """Return True if ticker is a valid normalised NSE ticker."""
    return ticker != "INVALID" and 2 <= len(ticker) <= 12
