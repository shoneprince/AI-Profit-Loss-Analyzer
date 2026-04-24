"""
Chart Generator Module

Creates all Plotly figures for the P&L Dashboard.
Uses a consistent dark professional theme across all charts.

Fixes v2:
  - Imports ALL keyword lists from financial_keywords.py (single source of truth)
  - Fixed _find_rows: removed `ll in kl` direction which caused short keywords
    like "sales", "revenue" to match any label that contained them AND caused
    "pat" to match "particulars". Now uses `kl in ll` only (keyword in label).
  - Added "profit / (loss) for the year" (space variant) to net income matching
  - Added NBFC revenue terms (interest income, dividend income, fair value gains)
  - Revenue-vs-expenses chart now uses full REVENUE_KEYWORDS list
  - Shared helpers (_get_label_col, _get_numeric_cols, _latest_col) extracted once
"""

import os
import re
import sys
import plotly.graph_objects as go
import pandas as pd

# ── Import central keyword registry ─────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
# Support both flat layout and src/dashboard/ layout
for _p in [_HERE, os.path.join(_HERE, "..", ".."), os.path.join(_HERE, "..")]:
    if os.path.exists(os.path.join(_p, "financial_keywords.py")):
        sys.path.insert(0, _p)
        break

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
    NET_INCOME_KEYWORDS,
    PBT_KEYWORDS,
    TAX_KEYWORDS,
    SKIP_ROW_KEYWORDS,
)


# ── Theme Constants ──────────────────────────────────────────────────

COLORS = {
    "primary": "#6366f1",       # Indigo
    "secondary": "#8b5cf6",     # Purple
    "success": "#22c55e",       # Green
    "danger": "#ef4444",        # Red
    "warning": "#f59e0b",       # Amber
    "info": "#06b6d4",          # Cyan
    "muted": "#64748b",         # Slate
    "bg": "#0f172a",            # Dark navy
    "card_bg": "#1e293b",       # Slate-800
    "text": "#f1f5f9",          # Slate-100
    "text_muted": "#94a3b8",    # Slate-400
    "grid": "#334155",          # Slate-700
}

CHART_PALETTE = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#22c55e",
    "#f59e0b", "#ef4444", "#ec4899", "#14b8a6",
]

_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=COLORS["text"], size=13),
    margin=dict(l=40, r=20, t=50, b=40),
    xaxis=dict(gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
    yaxis=dict(gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_muted"]),
    ),
)


def _apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply the standard dark theme to a figure."""
    fig.update_layout(**_LAYOUT_BASE, title=dict(
        text=title,
        font=dict(size=16, color=COLORS["text"]),
        x=0.02, xanchor="left",
    ))
    return fig


# ── Shared Data Helpers ──────────────────────────────────────────────

def _get_label_col(df: pd.DataFrame) -> str | None:
    """Find the first string/object column (row labels)."""
    for col in df.columns:
        if df[col].dtype == object:
            return col
    return None


def _get_numeric_cols(df: pd.DataFrame) -> list[str]:
    """Get all numeric column names (the period columns)."""
    return df.select_dtypes(include=["number"]).columns.tolist()


def _latest_col(num_cols: list[str]) -> str:
    """
    Return the column most likely to represent the latest/current period.
    Indian financial statements put the most recent year FIRST (left column).
    Falls back to num_cols[0].
    """
    if not num_cols:
        return ""
    best_col, best_year = num_cols[0], -1
    for col in num_cols:
        years = re.findall(r"20\d{2}", str(col))
        if years:
            y = max(int(y) for y in years)
            if y > best_year:
                best_year, best_col = y, col
    return best_col


def _find_rows(df: pd.DataFrame, keywords: list[str], label_col: str) -> pd.DataFrame:
    """
    Find rows whose label matches any keyword (keyword in label, case-insensitive).

    Matching rules:
      - Uses only forward direction: keyword is substring of label.
        e.g. keyword="revenue from operations" in label="revenue from operations" ✓
        e.g. keyword="revenue"                 in label="total revenue from ops"  ✓
      - Does NOT use (label in keyword) to avoid false positives such as
        short keyword "pat" matching the header row "particulars".
      - Skips rows matching SKIP_ROW_KEYWORDS (header/metadata rows).

    Row priority when multiple matches exist:
      "Total …" rows are moved to the front so that aggregate lines
      (e.g. "Total Revenue from operations") are preferred over component
      lines (e.g. "Interest Income", "Dividend Income") when the caller
      takes only the first matched row.
    """
    skip_lower = [s.lower() for s in SKIP_ROW_KEYWORDS]
    kw_lower = [kw.lower() for kw in keywords]

    def _matches(label: str) -> bool:
        ll = label.strip().lower()
        if any(skip in ll for skip in skip_lower):
            return False
        return any(kl in ll for kl in kw_lower)

    mask = df[label_col].astype(str).apply(_matches)
    matched = df[mask].copy()

    if matched.empty:
        return matched

    # Promote rows whose label starts with "total" to the very top.
    # This is critical for NBFC documents (e.g. Jio Financial) where
    # "Interest Income", "Dividend Income" etc. are all valid revenue
    # keyword matches but "Total Revenue from operations" is the correct
    # aggregate. Without this, iloc[0] would return Interest Income.
    labels_lower = matched[label_col].astype(str).str.strip().str.lower()
    is_total = labels_lower.str.startswith("total")
    # Also deprioritize header rows that matched but have no numeric value
    num_cols = matched.select_dtypes(include="number").columns.tolist()
    if num_cols:
        has_value = matched[num_cols].notna().any(axis=1)
        return pd.concat([
            matched[is_total & has_value],
            matched[~is_total & has_value],
            matched[is_total & ~has_value],
            matched[~is_total & ~has_value],
        ])


def _find_first_value(
    df: pd.DataFrame,
    keywords: list[str],
    label_col: str,
    target_col: str,
) -> float | None:
    """Return the first non-null value from target_col for a matching row."""
    rows = _find_rows(df, keywords, label_col)
    if rows.empty:
        return None
    val = rows.iloc[0].get(target_col)
    if val is not None and pd.notna(val):
        return float(val)
    return None


# ── Chart Builders ───────────────────────────────────────────────────

def create_revenue_vs_expenses_bar(df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar chart comparing key P&L items across all periods.
    Uses the full central keyword lists for reliable matching across
    US GAAP, Indian MCA, IFRS, NBFC, hospitality, and manufacturing formats.
    """
    label_col = _get_label_col(df)
    num_cols = _get_numeric_cols(df)

    if not label_col or not num_cols:
        return _empty_figure("Revenue vs Expenses")

    # Use central keyword lists — covers all document formats
    items = {
        "Revenue":        REVENUE_KEYWORDS,
        "Total Expenses": TOTAL_OPEX_KEYWORDS,
        "Net Income":     NET_INCOME_KEYWORDS,
    }

    fig = go.Figure()
    colors = [COLORS["primary"], COLORS["warning"], COLORS["success"]]
    traces_added = 0

    for i, (name, keywords) in enumerate(items.items()):
        rows = _find_rows(df, keywords, label_col)
        if rows.empty:
            continue
        row = rows.iloc[0]
        values = [row.get(c) for c in num_cols]
        # Only add trace if at least one value is non-null
        if not any(pd.notna(v) for v in values):
            continue
        fig.add_trace(go.Bar(
            name=name,
            x=num_cols,
            y=values,
            marker_color=colors[i % len(colors)],
            marker=dict(cornerradius=4),
            text=[
                f"₹{abs(v):,.0f}" if pd.notna(v) else ""
                for v in values
            ],
            textposition="outside",
            textfont=dict(size=11),
        ))
        traces_added += 1

    if traces_added == 0:
        return _empty_figure("Revenue vs Expenses")

    fig.update_layout(barmode="group", bargap=0.2, bargroupgap=0.1)
    return _apply_theme(fig, "📊 Revenue vs Key Expenses")


def create_expense_breakdown_pie(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart showing expense category breakdown for the latest period.
    Uses central keyword lists from financial_keywords.py.
    """
    label_col = _get_label_col(df)
    num_cols = _get_numeric_cols(df)

    if not label_col or not num_cols:
        return _empty_figure("Expense Breakdown")

    # Named expense categories using central keyword lists
    expense_categories: dict[str, list[str]] = {
        "Material / COGS":  COGS_KEYWORDS + INVENTORY_CHANGE_KEYWORDS,
        "Employee Costs":   EMPLOYEE_COST_KEYWORDS,
        "Finance Costs":    FINANCE_COST_KEYWORDS,
        "Depreciation":     DEPRECIATION_KEYWORDS,
        "SG&A":             SGA_KEYWORDS,
        "Marketing":        MARKETING_KEYWORDS,
        "R&D":              RD_KEYWORDS,
        "Tax":              TAX_KEYWORDS,
        "Other Expenses":   OTHER_EXPENSE_KEYWORDS,
    }

    latest_col = _latest_col(num_cols)
    if not latest_col:
        return _empty_figure("Expense Breakdown")

    labels = []
    values = []
    seen_rows: set = set()   # prevent double-counting

    for name, keywords in expense_categories.items():
        rows = _find_rows(df, keywords, label_col)
        for idx, row in rows.iterrows():
            if idx in seen_rows:
                continue
            val = row.get(latest_col) if latest_col in row.index else None
            if val is not None and pd.notna(val) and abs(float(val)) > 0:
                labels.append(name)
                values.append(abs(float(val)))
                seen_rows.add(idx)
                break   # one row per category

    if not labels:
        return _empty_figure("Expense Breakdown")

    # ── A3: Aggregate slices below 5% into "Other" ───────────
    total = sum(values)
    if total > 0:
        merged_labels, merged_values = [], []
        other_total = 0.0
        for lbl, val in zip(labels, values):
            if val / total < 0.05:
                other_total += val
            else:
                merged_labels.append(lbl)
                merged_values.append(val)
        if other_total > 0:
            merged_labels.append("Other")
            merged_values.append(other_total)
        labels, values = merged_labels, merged_values

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=CHART_PALETTE[:len(labels)]),
        textinfo="label+percent",
        textfont=dict(size=12),
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
    ))

    fig.add_annotation(
        text=f"<b>₹{total:,.0f}</b><br><span style='font-size:11px'>Total</span>",
        showarrow=False,
        font=dict(size=14, color=COLORS["text"]),
    )

    return _apply_theme(fig, f"🥧 Expense Breakdown ({latest_col})")


def create_margin_trend_line(kpis: dict) -> go.Figure:
    """
    Bar chart for available margin KPIs.
    """
    margins = {
        "Gross Margin":     kpis.get("gross_margin_pct"),
        "Operating Margin": kpis.get("operating_margin_pct"),
        "Net Margin":       kpis.get("net_margin_pct"),
        "Cost Ratio":       kpis.get("cost_ratio_pct"),
    }

    available = {k: v for k, v in margins.items() if v is not None}
    if not available:
        return _empty_figure("Margin Analysis")

    names = list(available.keys())
    values = list(available.values())
    colors_list = [COLORS["primary"], COLORS["success"], COLORS["info"], COLORS["warning"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names,
        y=values,
        marker_color=colors_list[:len(names)],
        marker=dict(cornerradius=6),
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        textfont=dict(size=14, color=COLORS["text"]),
        width=0.5,
    ))

    fig.update_yaxes(
        range=[min(0, min(values) * 1.2), max(values) * 1.3],
        title="Percentage (%)",
    )
    return _apply_theme(fig, "📈 Margin Analysis")


def create_waterfall_chart(df: pd.DataFrame) -> go.Figure:
    """
    Waterfall chart showing P&L bridge: Revenue → deductions → Net Income.
    Uses central keyword lists for all steps.
    """
    label_col = _get_label_col(df)
    num_cols = _get_numeric_cols(df)

    if not label_col or not num_cols:
        return _empty_figure("P&L Waterfall")

    latest_col = _latest_col(num_cols)

    steps: list[tuple[str, list[str], bool]] = [
        # (display_name, keyword_list, is_absolute_bar)
        ("Revenue",       REVENUE_KEYWORDS,                                True),
        ("Material/COGS", COGS_KEYWORDS + INVENTORY_CHANGE_KEYWORDS,       False),
        ("Employee",      EMPLOYEE_COST_KEYWORDS,                          False),
        ("Depreciation",  DEPRECIATION_KEYWORDS,                           False),
        ("Finance Costs", FINANCE_COST_KEYWORDS,                           False),
        ("SG&A",          SGA_KEYWORDS,                                    False),
        ("Marketing",     MARKETING_KEYWORDS,                              False),
        ("R&D",           RD_KEYWORDS,                                     False),
        ("Other Exp",     OTHER_EXPENSE_KEYWORDS,                          False),
        ("Tax",           TAX_KEYWORDS,                                    False),
        ("Net Income",    NET_INCOME_KEYWORDS,                              True),
    ]

    names = []
    values = []
    measures = []

    for step_name, keywords, is_absolute in steps:
        rows = _find_rows(df, keywords, label_col)
        if rows.empty:
            continue
        val = rows.iloc[0].get(latest_col)
        if val is None or pd.isna(val):
            continue
        val = float(val)
        names.append(step_name)
        if is_absolute:
            measures.append("absolute")
            values.append(val)
        else:
            measures.append("relative")
            values.append(-abs(val))

    if not names:
        return _empty_figure("P&L Waterfall")

    fig = go.Figure(go.Waterfall(
        name="P&L Bridge",
        orientation="v",
        measure=measures,
        x=names,
        y=values,
        textposition="outside",
        text=[f"₹{abs(v):,.0f}" for v in values],
        textfont=dict(size=11),
        connector=dict(line=dict(color=COLORS["grid"], width=1)),
        increasing=dict(marker_color=COLORS["success"]),
        decreasing=dict(marker_color=COLORS["danger"]),
        totals=dict(marker_color=COLORS["primary"]),
    ))

    return _apply_theme(fig, f"🏗️ P&L Bridge ({latest_col})")


def create_period_comparison_bar(df: pd.DataFrame) -> go.Figure:
    """
    Side-by-side comparison of key line items across periods.
    Only meaningful when multiple periods exist.
    """
    label_col = _get_label_col(df)
    num_cols = _get_numeric_cols(df)

    if not label_col or len(num_cols) < 2:
        return _empty_figure("Period Comparison")

    key_items = ["Revenue", "Cost of Goods Sold", "Gross Profit",
                 "Operating Income", "Net Income", "EBITDA"]

    filtered = df[df[label_col].isin(key_items)]
    if filtered.empty:
        filtered = df[df[label_col].str.lower().isin([k.lower() for k in key_items])]

    if filtered.empty:
        return _empty_figure("Period Comparison")

    fig = go.Figure()
    for i, col in enumerate(num_cols):
        fig.add_trace(go.Bar(
            name=col,
            x=filtered[label_col],
            y=filtered[col],
            marker_color=CHART_PALETTE[i % len(CHART_PALETTE)],
            marker=dict(cornerradius=4),
            text=[f"₹{v:,.0f}" if pd.notna(v) else "" for v in filtered[col]],
            textposition="outside",
            textfont=dict(size=10),
        ))

    fig.update_layout(barmode="group", bargap=0.15)
    return _apply_theme(fig, "📊 Period Comparison")


def create_kpi_indicators(kpis: dict) -> list[dict]:
    """
    Generate KPI card data for the dashboard layout.
    Returns a list of dicts: title, value, formatted, color, icon.
    """
    cards = []

    def _add(title, key, fmt="money", icon="💰"):
        val = kpis.get(key)
        if val is not None:
            if fmt == "money":
                if abs(val) >= 1_000_000:
                    formatted = f"₹{val / 1_000_000:,.1f}M"
                elif abs(val) >= 1_000:
                    formatted = f"₹{val / 1_000:,.1f}K"
                else:
                    formatted = f"₹{val:,.0f}"
                color = COLORS["success"] if val >= 0 else COLORS["danger"]
            elif fmt == "pct":
                formatted = f"{val:.1f}%"
                color = COLORS["success"] if val >= 20 else (
                    COLORS["warning"] if val >= 10 else COLORS["danger"]
                )
            else:
                formatted = str(val)
                color = COLORS["info"]

            cards.append({
                "title": title,
                "value": val,
                "formatted": formatted,
                "color": color,
                "icon": icon,
            })

    _add("Revenue", "revenue", "money", "💰")
    _add("Net Income", "net_income", "money", "📈")
    _add("Gross Profit", "gross_profit", "money", "📊")
    _add("EBITDA", "ebitda", "money", "🏦")
    _add("Gross Margin", "gross_margin_pct", "pct", "📉")
    _add("Operating Margin", "operating_margin_pct", "pct", "⚙️")
    _add("Net Margin", "net_margin_pct", "pct", "🎯")
    _add("Cost Ratio", "cost_ratio_pct", "pct", "💸")

    return cards


# ── Utility ──────────────────────────────────────────────────────────

def _empty_figure(title: str) -> go.Figure:
    """Create an empty figure with a 'No data' message."""
    fig = go.Figure()
    fig.add_annotation(
        text="No data available",
        showarrow=False,
        font=dict(size=16, color=COLORS["text_muted"]),
        xref="paper", yref="paper", x=0.5, y=0.5,
    )
    return _apply_theme(fig, title)