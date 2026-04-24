"""
KPI Extraction Engine

Deterministic Python calculations for key financial metrics.
Computed WITHOUT the LLM, then fed into the RAG pipeline.

All keyword matching is sourced from financial_keywords.py so
there is one place to add new label variants.
"""

import os
import sys
import difflib
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from financial_keywords import (
    REVENUE_KEYWORDS,
    OTHER_INCOME_KEYWORDS,
    COGS_KEYWORDS,
    INVENTORY_CHANGE_KEYWORDS,
    GROSS_PROFIT_KEYWORDS,
    EMPLOYEE_COST_KEYWORDS,
    DEPRECIATION_KEYWORDS,
    FINANCE_COST_KEYWORDS,
    SGA_KEYWORDS,
    MARKETING_KEYWORDS,
    RD_KEYWORDS,
    OTHER_EXPENSE_KEYWORDS,
    TOTAL_OPEX_KEYWORDS,
    OPERATING_INCOME_KEYWORDS,
    EBITDA_KEYWORDS,
    PBT_KEYWORDS,
    TAX_KEYWORDS,
    NET_INCOME_KEYWORDS,
    SKIP_ROW_KEYWORDS,
)


# ── Internal helpers ─────────────────────────────────────────────────

def _get_label_col(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if df[col].dtype == object:
            return col
    return None


def _get_numeric_cols(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["number"]).columns.tolist()


def _is_skip_row(label: str) -> bool:
    ll = label.strip().lower()
    return any(kw in ll for kw in SKIP_ROW_KEYWORDS)


def _find_value(df: pd.DataFrame, keywords: list[str]) -> float | None:
    """
    Search the DataFrame for a row whose label matches any keyword.

    Priority:
      1. Exact match  (label == keyword) — checked across all rows first
      2. "Total …" rows with substring match — preferred over component rows
         so "Total Revenue from operations" beats "Interest Income" for revenue
      3. Any substring match  (keyword in label)
      4. Fuzzy match  (similarity > 0.82, keywords > 5 chars)
         — catches OCR errors like "Reuenue" → "Revenue"

    Returns the value from the LATEST (first/leftmost) numeric column, or None.
    """
    label_col = _get_label_col(df)
    if label_col is None:
        return None

    numeric_cols = _get_numeric_cols(df)
    if not numeric_cols:
        return None

    kw_lower = [k.lower() for k in keywords]

    def _get_val(row) -> float | None:
        """Return first non-null value from numeric cols (latest period first)."""
        for nc in numeric_cols:
            val = row[nc]
            if pd.notna(val):
                return float(val)
        return None

    # Build candidate rows with their match tier.
    #
    # Tier priority (highest first):
    #   Tier 0: label starts with "total" AND keyword is substring of label
    #           e.g. "Total Revenue from operations" beats "Interest Income"
    #           even when "interest income" is an exact keyword match.
    #   Tier 1: exact match (label == keyword), non-total rows
    #   Tier 2: keyword is substring of label, non-total rows
    #   Tier 3: fuzzy match (OCR resilience, similarity > 0.82)
    #
    # Keeping total-aggregate rows at Tier 0 is critical for NBFC / financial
    # services documents (e.g. Jio Financial) where individual revenue streams
    # (Interest Income, Dividend Income, …) are all valid keyword matches but
    # the summary "Total Revenue from operations" is the correct KPI value.
    tier0, tier1, tier2, tier3 = [], [], [], []

    for _, row in df.iterrows():
        label = str(row[label_col]).strip().lower()
        if not label or _is_skip_row(label):
            continue

        is_total = label.startswith("total")
        matched_sub = any(kw in label for kw in kw_lower)

        if matched_sub and is_total:
            tier0.append(row)
        elif label in kw_lower:
            tier1.append(row)
        elif matched_sub:
            tier2.append(row)
        else:
            matched_fuzzy = any(
                len(kw) > 5 and difflib.SequenceMatcher(None, kw, label).ratio() > 0.82
                for kw in kw_lower
            )
            if matched_fuzzy:
                tier3.append(row)

    for candidates in (tier0, tier1, tier2, tier3):
        for row in candidates:
            v = _get_val(row)
            if v is not None:
                return v

    return None


# ── Margin / ratio calculators ───────────────────────────────────────

def compute_gross_margin(revenue: float, cogs: float) -> float | None:
    if revenue and revenue != 0:
        return round((revenue - cogs) / revenue * 100, 2)
    return None


def compute_operating_margin(operating_income: float, revenue: float) -> float | None:
    if revenue and revenue != 0:
        return round(operating_income / revenue * 100, 2)
    return None


def compute_net_margin(net_income: float, revenue: float) -> float | None:
    if revenue and revenue != 0:
        return round(net_income / revenue * 100, 2)
    return None


def compute_revenue_growth(current: float, previous: float) -> float | None:
    if previous and previous != 0:
        return round((current - previous) / previous * 100, 2)
    return None


def compute_cost_ratio(total_expenses: float, revenue: float) -> float | None:
    if revenue and revenue != 0:
        return round(total_expenses / revenue * 100, 2)
    return None


def compute_ebitda(operating_income: float, depreciation: float) -> float | None:
    if operating_income is not None and depreciation is not None:
        return round(operating_income + depreciation, 2)
    return None


# ── Main extractor ───────────────────────────────────────────────────

def extract_kpis(df: pd.DataFrame) -> dict:
    """
    Extract all available KPIs from a cleaned P&L DataFrame.
    Applies multi-level fallback logic so partial documents still
    produce useful metrics.
    """
    # ── Raw lookups ───────────────────────────────────────────────
    revenue          = _find_value(df, REVENUE_KEYWORDS)

    # Revenue fallback: holding companies (e.g. ICF) may have zero operating
    # revenue — their "Revenue from operations" row exists but has no value.
    # Fall back to "Total Income" (which includes other income) in that case.
    if revenue is None:
        revenue = _find_value(df, ["total income", "total revenue",
                                   "total income from operations"])
    # Last resort: use "Other income" if that's the only income line
    if revenue is None:
        revenue = _find_value(df, OTHER_INCOME_KEYWORDS)
    cogs             = _find_value(df, COGS_KEYWORDS)
    inventory_change = _find_value(df, INVENTORY_CHANGE_KEYWORDS)
    gross_profit     = _find_value(df, GROSS_PROFIT_KEYWORDS)
    employee_cost    = _find_value(df, EMPLOYEE_COST_KEYWORDS)
    depreciation     = _find_value(df, DEPRECIATION_KEYWORDS)
    finance_costs    = _find_value(df, FINANCE_COST_KEYWORDS)
    marketing        = _find_value(df, MARKETING_KEYWORDS)
    rd               = _find_value(df, RD_KEYWORDS)
    sga              = _find_value(df, SGA_KEYWORDS)
    other_expenses   = _find_value(df, OTHER_EXPENSE_KEYWORDS)
    total_opex       = _find_value(df, TOTAL_OPEX_KEYWORDS)
    operating_income = _find_value(df, OPERATING_INCOME_KEYWORDS)
    ebitda           = _find_value(df, EBITDA_KEYWORDS)
    pbt              = _find_value(df, PBT_KEYWORDS)
    tax_expense      = _find_value(df, TAX_KEYWORDS)
    net_income       = _find_value(df, NET_INCOME_KEYWORDS)

    # ── Fallback / derivation ─────────────────────────────────────

    # Combine COGS + inventory change (Indian manufacturing format)
    if cogs is not None and inventory_change is not None:
        cogs = cogs + inventory_change

    # Gross profit from revenue - cogs if row absent
    if gross_profit is None and revenue is not None and cogs is not None:
        gross_profit = round(revenue - cogs, 2)

    # Operating income falls back to PBT for simple single-entity P&Ls
    if operating_income is None and pbt is not None:
        operating_income = pbt

    # EBITDA from operating income + depreciation if row absent
    if ebitda is None:
        ebitda = compute_ebitda(operating_income, depreciation)

    # Total opex from component sum if total row absent
    if total_opex is None:
        components = [cogs, employee_cost, depreciation, finance_costs,
                      marketing, rd, sga, other_expenses]
        known = [v for v in components if v is not None]
        if len(known) >= 2:
            total_opex = round(sum(known), 2)

    # Net income from PBT - tax if bottom line row absent
    if net_income is None and pbt is not None and tax_expense is not None:
        net_income = round(pbt - tax_expense, 2)

    # ── Build KPI dict ────────────────────────────────────────────
    kpis: dict = {
        "revenue":              revenue,
        "cogs":                 cogs,
        "gross_profit":         gross_profit,
        "employee_cost":        employee_cost,
        "depreciation":         depreciation,
        "finance_costs":        finance_costs,
        "total_opex":           total_opex,
        "operating_income":     operating_income,
        "ebitda":               ebitda,
        "pbt":                  pbt,
        "tax_expense":          tax_expense,
        "net_income":           net_income,
        "gross_margin_pct":     None,
        "operating_margin_pct": None,
        "net_margin_pct":       None,
        "ebitda_margin_pct":    None,
        "cost_ratio_pct":       None,
        "revenue_growth_pct":   None,
        "net_income_growth_pct": None,
        "expense_growth_pct":   None,
        "latest_period":        None,
    }

    # ── Margin KPIs ───────────────────────────────────────────────
    if revenue:
        if cogs is not None:
            kpis["gross_margin_pct"] = compute_gross_margin(revenue, cogs)
        elif gross_profit is not None:
            kpis["gross_margin_pct"] = round(gross_profit / revenue * 100, 2)

        if operating_income is not None:
            kpis["operating_margin_pct"] = compute_operating_margin(
                operating_income, revenue
            )
        if net_income is not None:
            kpis["net_margin_pct"] = compute_net_margin(net_income, revenue)
        if ebitda is not None:
            kpis["ebitda_margin_pct"] = round(ebitda / revenue * 100, 2)
        if total_opex is not None:
            kpis["cost_ratio_pct"] = compute_cost_ratio(total_opex, revenue)

    # ── Multi-period growth KPIs ──────────────────────────────────
    numeric_cols = _get_numeric_cols(df)
    if numeric_cols:
        kpis["latest_period"] = str(numeric_cols[0])

    if len(numeric_cols) >= 2:
        prev_revenue = _find_value_for_col(df, REVENUE_KEYWORDS, numeric_cols[1])
        prev_net     = _find_value_for_col(df, NET_INCOME_KEYWORDS, numeric_cols[1])
        prev_opex    = _find_value_for_col(df, TOTAL_OPEX_KEYWORDS, numeric_cols[1])

        if revenue is not None and prev_revenue:
            kpis["revenue_growth_pct"] = compute_revenue_growth(revenue, prev_revenue)
        if net_income is not None and prev_net:
            kpis["net_income_growth_pct"] = compute_revenue_growth(net_income, prev_net)
        if total_opex is not None and prev_opex:
            kpis["expense_growth_pct"] = compute_revenue_growth(total_opex, prev_opex)

    available = {k: v for k, v in kpis.items() if v is not None}
    print(f"[KPI Engine] Extracted {len(available)} KPIs: {list(available.keys())}")
    return kpis


def _find_value_for_col(
    df: pd.DataFrame, keywords: list[str], target_col: str
) -> float | None:
    """
    Like _find_value but returns the value from a specific column
    (used for previous-period lookups).
    """
    label_col = _get_label_col(df)
    if label_col is None or target_col not in df.columns:
        return None

    kw_lower = [k.lower() for k in keywords]

    for _, row in df.iterrows():
        label = str(row[label_col]).strip().lower()
        if not label or _is_skip_row(label):
            continue
        is_total = label.startswith("total")
        matched = any(kw in label for kw in kw_lower)
        if matched and is_total:
            val = row.get(target_col)
            if pd.notna(val):
                return float(val)

    for _, row in df.iterrows():
        label = str(row[label_col]).strip().lower()
        if not label or _is_skip_row(label):
            continue
        if any(kw in label for kw in kw_lower):
            val = row.get(target_col)
            if pd.notna(val):
                return float(val)

    return None