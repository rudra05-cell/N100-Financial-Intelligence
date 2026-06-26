"""
src/etl/loader.py
Main ETL loader for the Nifty 100 Financial Intelligence Platform.
Reads all 12 Excel source files, normalises, validates, and loads
into the SQLite database (nifty100.db).

Usage:
    python src/etl/loader.py
    OR:  make load
"""

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

from normaliser import normalize_year, normalize_ticker, is_valid_year, is_valid_ticker
from validator import run_all_dq_rules

# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path="config/.env.template")   # load .env if present

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

DB_PATH          = os.getenv("DB_PATH",          "data/nifty100.db")
RAW_DIR          = os.getenv("RAW_DATA_DIR",     "data/raw")
SUPP_DIR         = os.getenv("SUPPORTING_DATA_DIR","data/supporting")
OUTPUT_DIR       = os.getenv("OUTPUT_DIR",       "output")
SCHEMA_PATH      = "db/schema.sql"

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path("data").mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# File Manifest
# Core files:  header=1  (Row 0 is metadata, Row 1 is actual headers)
# Supplementary files:  header=0
# ──────────────────────────────────────────────────────────────────────────────
CORE_FILES = {
    "companies":     {"path": f"{RAW_DIR}/companies.xlsx",     "header": 1, "table": "companies"},
    "profitandloss": {"path": f"{RAW_DIR}/profitandloss.xlsx", "header": 1, "table": "profitandloss"},
    "balancesheet":  {"path": f"{RAW_DIR}/balancesheet.xlsx",  "header": 1, "table": "balancesheet"},
    "cashflow":      {"path": f"{RAW_DIR}/cashflow.xlsx",      "header": 1, "table": "cashflow"},
    "analysis":      {"path": f"{RAW_DIR}/analysis.xlsx",      "header": 1, "table": "analysis"},
    "documents":     {"path": f"{RAW_DIR}/documents.xlsx",     "header": 1, "table": "documents"},
    "prosandcons":   {"path": f"{RAW_DIR}/prosandcons.xlsx",   "header": 1, "table": "prosandcons"},
}

SUPPLEMENTARY_FILES = {
    "sectors":          {"path": f"{SUPP_DIR}/sectors.xlsx",         "header": 0, "table": "sectors"},
    "stock_prices":     {"path": f"{SUPP_DIR}/stock_prices.xlsx",    "header": 0, "table": "stock_prices"},
    "financial_ratios": {"path": f"{SUPP_DIR}/financial_ratios.xlsx","header": 0, "table": "financial_ratios"},
}

# Load order matters due to FK constraints
LOAD_ORDER = [
    "companies",        # Must be first — parent table
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "financial_ratios",
]

ALL_FILES = {**CORE_FILES, **SUPPLEMENTARY_FILES}


# ──────────────────────────────────────────────────────────────────────────────
# Excel Loader
# ──────────────────────────────────────────────────────────────────────────────

def load_excel(path: str, header_row: int = 1) -> Optional[pd.DataFrame]:
    """
    Load an Excel file into a DataFrame.
    header=1 means row index 1 (2nd row) contains column headers.
    Returns None if file does not exist.
    """
    if not Path(path).exists():
        logger.warning("File not found (skip): %s", path)
        return None

    try:
        df = pd.read_excel(path, header=header_row, engine="openpyxl")
        # Strip whitespace from all string columns
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("nan", pd.NA)
        logger.info("Loaded %s: %d rows × %d cols", Path(path).name, len(df), len(df.columns))
        return df
    except Exception as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Table-specific normalisation
# ──────────────────────────────────────────────────────────────────────────────

def normalise_companies(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Normalise companies DataFrame. Returns (clean_df, rejected_count)."""
    df = df.copy()
    df["id"] = df["id"].apply(normalize_ticker)
    rejected = df[df["id"] == "INVALID"]
    df = df[df["id"] != "INVALID"].drop_duplicates(subset="id", keep="last")
    return df, len(rejected)


def normalise_time_series(df: pd.DataFrame, table_name: str) -> tuple[pd.DataFrame, int]:
    """
    Normalise a time-series table (P&L, BS, CF).
    - Normalise company_id (ticker)
    - Normalise year labels
    - Drop rows with INVALID ticker or PARSE_ERROR year
    - Deduplicate on (company_id, year) — keep last
    Returns (clean_df, rejected_count)
    """
    df = df.copy()

    # Normalise ticker
    df["company_id"] = df["company_id"].apply(normalize_ticker)

    # Normalise year
    df["year"] = df["year"].apply(normalize_year)

    # Identify rejects
    invalid_ticker = df["company_id"] == "INVALID"
    parse_error_yr = df["year"] == "PARSE_ERROR"
    rejected_count = int((invalid_ticker | parse_error_yr).sum())

    if rejected_count > 0:
        logger.warning(
            "%s: rejecting %d rows (invalid ticker or unparseable year)",
            table_name, rejected_count,
        )

    # Keep valid rows only
    df = df[~(invalid_ticker | parse_error_yr)]

    # Fix negative fixed_assets (DQ-10 coerce)
    if "fixed_assets" in df.columns:
        neg_mask = df["fixed_assets"].notna() & (df["fixed_assets"] < 0)
        if neg_mask.any():
            logger.warning("%s: coercing %d negative fixed_asset rows to 0",
                           table_name, int(neg_mask.sum()))
            df.loc[neg_mask, "fixed_assets"] = 0

    # Deduplicate — keep last occurrence
    before = len(df)
    df = df.drop_duplicates(subset=["company_id", "year"], keep="last")
    dupes_removed = before - len(df)
    if dupes_removed > 0:
        logger.warning("%s: removed %d duplicate (company_id, year) rows",
                       table_name, dupes_removed)

    return df, rejected_count


def normalise_analysis(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "INVALID").sum())
    df = df[df["company_id"] != "INVALID"]
    return df, rejected


def normalise_documents(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "INVALID").sum())
    df = df[df["company_id"] != "INVALID"]
    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(0).astype(int)
    return df, rejected


def normalise_prosandcons(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "INVALID").sum())
    df = df[df["company_id"] != "INVALID"]
    return df, rejected


def normalise_sectors(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "INVALID").sum())
    df = df[df["company_id"] != "INVALID"].drop_duplicates(subset="company_id", keep="last")
    return df, rejected


def normalise_stock_prices(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "INVALID").sum())
    df = df[df["company_id"] != "INVALID"]
    return df, rejected


def normalise_financial_ratios(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    if "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)
        df = df[df["year"] != "PARSE_ERROR"]
    rejected = int((df["company_id"] == "INVALID").sum())
    df = df[df["company_id"] != "INVALID"]
    return df, rejected


NORMALISE_MAP = {
    "companies":      normalise_companies,
    "profitandloss":  lambda df: normalise_time_series(df, "profitandloss"),
    "balancesheet":   lambda df: normalise_time_series(df, "balancesheet"),
    "cashflow":       lambda df: normalise_time_series(df, "cashflow"),
    "analysis":       normalise_analysis,
    "documents":      normalise_documents,
    "prosandcons":    normalise_prosandcons,
    "sectors":        normalise_sectors,
    "stock_prices":   normalise_stock_prices,
    "financial_ratios": normalise_financial_ratios,
}


# ──────────────────────────────────────────────────────────────────────────────
# SQLite database initialisation
# ──────────────────────────────────────────────────────────────────────────────

def init_database(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Create the SQLite database and apply schema.sql.
    Enables foreign key constraints.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    logger.info("Database initialised: %s", db_path)
    return conn


# ──────────────────────────────────────────────────────────────────────────────
# Load a single table
# ──────────────────────────────────────────────────────────────────────────────

def load_table(
    conn: sqlite3.Connection,
    table_name: str,
    df: pd.DataFrame,
) -> dict:
    """
    Load a DataFrame into the specified SQLite table.
    Uses INSERT OR REPLACE to handle re-runs (idempotent).
    Returns audit record dict.
    """
    t0 = time.time()
    rows_in = len(df)

    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()
        rows_out = pd.read_sql(f"SELECT COUNT(*) as n FROM {table_name}", conn).iloc[0]["n"]
        status = "OK"
        error_msg = None
    except Exception as exc:
        logger.error("Failed to load table %s: %s", table_name, exc)
        rows_out = 0
        status = "FAILED"
        error_msg = str(exc)

    runtime = round(time.time() - t0, 3)

    return {
        "table":      table_name,
        "rows_in":    rows_in,
        "rows_out":   int(rows_out) if rows_out else 0,
        "rejected":   rows_in - int(rows_out) if rows_out else rows_in,
        "status":     status,
        "error":      error_msg,
        "timestamp":  datetime.now().isoformat(),
        "runtime_s":  runtime,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def run_full_load() -> dict[str, pd.DataFrame]:
    """
    Execute the full ETL pipeline:
    1. Load all 12 Excel files
    2. Normalise each DataFrame
    3. Run DQ validation
    4. Load into SQLite
    5. Write load_audit.csv
    6. Run FK check

    Returns dict of all loaded DataFrames (for use by downstream modules).
    """
    logger.info("=" * 60)
    logger.info("Nifty 100 ETL — Full Load Starting")
    logger.info("=" * 60)

    # ── Step 1: Load raw Excel files ──────────────────────────
    loaded_raw: dict[str, Optional[pd.DataFrame]] = {}
    for name in LOAD_ORDER:
        if name not in ALL_FILES:
            continue
        meta = ALL_FILES[name]
        df_raw = load_excel(meta["path"], header_row=meta["header"])
        loaded_raw[name] = df_raw

    # ── Step 2: Normalise ─────────────────────────────────────
    loaded_clean: dict[str, pd.DataFrame] = {}
    for name in LOAD_ORDER:
        df = loaded_raw.get(name)
        if df is None:
            logger.warning("Skipping %s (file not available)", name)
            continue
        norm_fn = NORMALISE_MAP.get(name)
        if norm_fn:
            clean_df, rejected = norm_fn(df)
        else:
            clean_df, rejected = df.copy(), 0
        logger.info("Normalised %s: %d rows in, %d rejected, %d clean",
                    name, len(df), rejected, len(clean_df))
        loaded_clean[name] = clean_df

    # ── Step 3: DQ Validation ─────────────────────────────────
    logger.info("Running DQ validation rules...")
    failures_df = run_all_dq_rules(
        companies     = loaded_clean.get("companies",     pd.DataFrame()),
        profitandloss = loaded_clean.get("profitandloss", pd.DataFrame()),
        balancesheet  = loaded_clean.get("balancesheet",  pd.DataFrame()),
        cashflow      = loaded_clean.get("cashflow",      pd.DataFrame()),
        output_path   = f"{OUTPUT_DIR}/validation_failures.csv",
    )
    critical_count = len(failures_df[failures_df["severity"] == "CRITICAL"])
    if critical_count > 0:
        logger.error(
            "CRITICAL DQ failures detected (%d). "
            "Proceeding with load but manual review required.",
            critical_count,
        )

    # ── Step 4: Database Load ─────────────────────────────────
    conn = init_database(DB_PATH)
    audit_records = []

    for name in LOAD_ORDER:
        df = loaded_clean.get(name)
        if df is None or df.empty:
            logger.warning("No data for table %s — skipping", name)
            continue
        audit_rec = load_table(conn, name, df)
        audit_records.append(audit_rec)
        logger.info("Loaded %s: %d rows → DB", name, audit_rec["rows_out"])

    # ── Step 5: Write Load Audit ──────────────────────────────
    audit_df = pd.DataFrame(audit_records)
    audit_path = f"{OUTPUT_DIR}/load_audit.csv"
    audit_df.to_csv(audit_path, index=False)
    logger.info("Load audit written to %s", audit_path)

    # ── Step 6: FK Integrity Check ────────────────────────────
    logger.info("Running PRAGMA foreign_key_check...")
    fk_issues = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_issues:
        logger.error("FK check FAILED: %d violations found", len(fk_issues))
        for issue in fk_issues:
            logger.error("  FK violation: %s", issue)
    else:
        logger.info("FK check PASSED: 0 violations")

    # ── Final Summary ─────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("ETL COMPLETE")
    logger.info("Tables loaded:   %d", len(audit_records))
    logger.info("DQ failures:     %d CRITICAL, %d WARNING",
                critical_count,
                len(failures_df[failures_df["severity"] == "WARNING"]))
    logger.info("FK violations:   %d", len(fk_issues))
    logger.info("DB path:         %s", DB_PATH)
    logger.info("=" * 60)

    conn.close()
    return loaded_clean


if __name__ == "__main__":
    run_full_load()
