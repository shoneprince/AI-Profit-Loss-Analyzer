"""
Data Cleaning Module

Cleans and normalises parsed P&L DataFrames:
  - Removes empty rows/columns
  - Normalises currency strings to numeric values
  - Standardises column names and row labels
  - Drops metadata columns (note numbers, schedule numbers)

Label aliases are sourced from financial_keywords.LABEL_ALIAS_MAP
so there is one place to update matching vocabulary.
"""

import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from financial_keywords import LABEL_ALIAS_MAP, SKIP_ROW_KEYWORDS


# ── Basic structural cleaning ────────────────────────────────────────

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop fully-empty rows/columns, strip whitespace, reset index."""
    df = df.dropna(how="all").dropna(axis=1, how="all")
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


# ── Currency normalisation ───────────────────────────────────────────

def normalize_currency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert currency-formatted strings to float values.

    Handles:
      $1,234.56  →  1234.56
      (500)      → -500         (accounting negative)
      -          →  NaN
      ₹, €, £, ¥, kr, CHF stripped automatically
    """
    def _to_numeric(value):
        if not isinstance(value, str):
            return value
        s = value.strip()

        # Null-like strings
        if s in ("", "-", "—", "–", "nan", "None", "nil", "Nil", "NIL",
                 "n/a", "N/A", "N.A.", "na"):
            return None

        # Accounting-style negatives: (1,234)
        is_negative = False
        if s.startswith("(") and s.endswith(")"):
            is_negative = True
            s = s[1:-1]

        # Strip currency symbols, thousand separators, spaces
        s = re.sub(r"[₹$€£¥,\s]", "", s)
        # Strip multi-char currency codes that may appear after OCR
        s = re.sub(r"(?i)^(inr|usd|gbp|eur|cad|aud|chf|kr|rs\.?)\s*", "", s)
        s = s.strip()

        try:
            val = float(s)
            return -val if is_negative else val
        except ValueError:
            return value  # not a number — leave as-is

    for col in df.select_dtypes(include=["object"]).columns:
        converted = df[col].apply(_to_numeric)
        numeric_mask = converted.apply(lambda x: isinstance(x, (int, float)))
        # Only convert the column if > 50 % of its values are numeric
        if numeric_mask.sum() > len(converted) * 0.5:
            df[col] = converted.apply(
                lambda x: float(x) if isinstance(x, (int, float)) else None
            ).astype(float)

    return df


# ── Column name standardisation ──────────────────────────────────────

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise column names (lowercase, collapsed spaces) and
    standardise row labels in the first string column using
    LABEL_ALIAS_MAP from financial_keywords.py.
    """
    # Normalise column names
    df.columns = [
        re.sub(r"\s+", " ", str(c).strip().lower()) for c in df.columns
    ]

    # Deduplicate column names
    seen: set = set()
    new_cols = []
    for c in df.columns:
        c_str = str(c)
        if c_str in seen:
            i = 1
            while f"{c_str}_{i}" in seen:
                i += 1
            c_str = f"{c_str}_{i}"
        seen.add(c_str)
        new_cols.append(c_str)
    df.columns = new_cols

    # Standardise the row-label column
    label_col = None
    for col in df.columns:
        if df[col].dtype == object:
            label_col = col
            break

    if label_col is not None:
        df[label_col] = df[label_col].apply(_standardize_label)

    return df


def _standardize_label(label: str) -> str:
    """
    Map a raw row label to its canonical name.

    Strategy:
      1. Exact key lookup in LABEL_ALIAS_MAP
      2. Partial-key lookup (alias key is substring of label)
         — covers verbose variants like
           "profit from continuing operation (after tax)" → "Net Income"
    """
    if not isinstance(label, str):
        return str(label)

    key = label.strip().lower()

    # 1. Exact match
    if key in LABEL_ALIAS_MAP:
        return LABEL_ALIAS_MAP[key]

    # 2. Partial match — walk aliases, longest match wins
    best_len = 0
    best_canonical = label.strip()
    for alias_key, canonical in LABEL_ALIAS_MAP.items():
        if len(alias_key) > 4 and alias_key in key:
            if len(alias_key) > best_len:
                best_len = len(alias_key)
                best_canonical = canonical

    return best_canonical


# ── Metadata column removal ──────────────────────────────────────────

def remove_metadata_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop columns that carry reference numbers, not financial data.
    Examples: "Note No.", "Schedule", "Sch.", "Sr. No."
    """
    drop_cols = []
    for col in df.columns:
        c = str(col).lower().strip()
        if c in {"note", "notes", "note no", "note no.", "sch", "sch.",
                 "schedule", "schedule no", "schedule no.",
                 "sr no", "sr. no", "serial no", "ref", "ref."}:
            drop_cols.append(col)
        elif re.search(r"\bnote\b.*\bno\b", c):
            drop_cols.append(col)
        elif re.search(r"\bschedule\b.*\bno\b", c):
            drop_cols.append(col)

    if drop_cols:
        df = df.drop(columns=drop_cols)
    return df


# ── Full pipeline ────────────────────────────────────────────────────

def clean_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Run all cleaning steps in order."""
    print("[Cleaner] Cleaning DataFrame …")
    df = clean_dataframe(df)
    df = normalize_currency(df)
    df = standardize_columns(df)
    df = remove_metadata_columns(df)
    print(f"[Cleaner] Done — {len(df)} rows × {len(df.columns)} columns")
    return df