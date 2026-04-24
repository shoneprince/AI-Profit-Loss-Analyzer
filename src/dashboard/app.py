"""
P&L Summarizer — Interactive Dashboard

Plotly Dash web application with:
- File upload (drag & drop for PDF, Excel, CSV)
- Auto-generated KPI cards and interactive charts
- Embedded RAG chat for AI-powered Q&A
- Dark professional theme

Run:  python -m src.dashboard.app
Open: http://127.0.0.1:8050
"""

import base64
import io
import os
import sys
import tempfile

import pandas as pd
from dash import Dash, html, dcc, Input, Output, State, callback, no_update
import plotly.graph_objects as go

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.ingestion.parser import ingest_document
from src.ingestion.cleaner import clean_pipeline
from src.analysis.kpi_engine import extract_kpis
from src.dashboard.chart_generator import (
    create_revenue_vs_expenses_bar,
    create_expense_breakdown_pie,
    create_margin_trend_line,
    create_waterfall_chart,
    create_period_comparison_bar,
    create_kpi_indicators,
    COLORS,
)


# ── App Initialization ───────────────────────────────────────────────

app = Dash(
    __name__,
    title="P&L Analyzer Dashboard",
    update_title="Analyzing...",
    suppress_callback_exceptions=True,
)

# Store for pipeline state (cleaned df, kpis, rag chain)
_state = {
    "df": None,
    "kpis": {},
    "chain_fn": None,
    "filename": None,
}


# ── CSS Styles ───────────────────────────────────────────────────────

STYLES = {
    "page": {
        "backgroundColor": COLORS["bg"],
        "minHeight": "100vh",
        "fontFamily": "'Inter', 'Segoe UI', sans-serif",
        "color": COLORS["text"],
        "padding": "0",
        "margin": "0",
    },
    "header": {
        "background": "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        "padding": "24px 40px",
        "borderBottom": f"1px solid {COLORS['grid']}",
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
    },
    "title": {
        "fontSize": "24px",
        "fontWeight": "700",
        "color": COLORS["text"],
        "margin": "0",
        "letterSpacing": "-0.5px",
    },
    "subtitle": {
        "fontSize": "13px",
        "color": COLORS["text_muted"],
        "margin": "0",
    },
    "main": {
        "padding": "24px 40px",
        "maxWidth": "1400px",
        "margin": "0 auto",
    },
    "upload_zone": {
        "border": f"2px dashed {COLORS['grid']}",
        "borderRadius": "12px",
        "padding": "40px",
        "textAlign": "center",
        "cursor": "pointer",
        "transition": "all 0.2s ease",
        "backgroundColor": COLORS["card_bg"],
        "marginBottom": "24px",
    },
    "kpi_grid": {
        "display": "grid",
        "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))",
        "gap": "16px",
        "marginBottom": "24px",
    },
    "kpi_card": {
        "backgroundColor": COLORS["card_bg"],
        "borderRadius": "12px",
        "padding": "20px",
        "border": f"1px solid {COLORS['grid']}",
        "textAlign": "center",
    },
    "chart_grid": {
        "display": "grid",
        "gridTemplateColumns": "repeat(2, 1fr)",
        "gap": "20px",
        "marginBottom": "24px",
    },
    "chart_card": {
        "backgroundColor": COLORS["card_bg"],
        "borderRadius": "12px",
        "padding": "16px",
        "border": f"1px solid {COLORS['grid']}",
    },
    "chat_container": {
        "backgroundColor": COLORS["card_bg"],
        "borderRadius": "12px",
        "padding": "20px",
        "border": f"1px solid {COLORS['grid']}",
        "marginBottom": "24px",
    },
    "chat_input_area": {
        "display": "flex",
        "gap": "12px",
        "marginTop": "12px",
    },
    "chat_input": {
        "flex": "1",
        "padding": "12px 16px",
        "borderRadius": "8px",
        "border": f"1px solid {COLORS['grid']}",
        "backgroundColor": COLORS["bg"],
        "color": COLORS["text"],
        "fontSize": "14px",
        "outline": "none",
    },
    "chat_button": {
        "padding": "12px 24px",
        "borderRadius": "8px",
        "border": "none",
        "backgroundColor": COLORS["primary"],
        "color": "white",
        "fontWeight": "600",
        "cursor": "pointer",
        "fontSize": "14px",
    },
    "chat_response": {
        "backgroundColor": COLORS["bg"],
        "borderRadius": "8px",
        "padding": "16px",
        "marginTop": "12px",
        "fontSize": "14px",
        "lineHeight": "1.6",
        "whiteSpace": "pre-wrap",
        "maxHeight": "300px",
        "overflowY": "auto",
    },
}


# ── Layout ───────────────────────────────────────────────────────────

app.layout = html.Div(style=STYLES["page"], children=[
    # Header
    html.Div(style=STYLES["header"], children=[
        html.Div([
            html.H1("📊 P&L Analyzer Dashboard", style=STYLES["title"]),
            html.P("Upload a P&L file to auto-generate financial insights",
                   style=STYLES["subtitle"]),
        ]),
        html.Div(id="file-badge", style={"display": "none"}),
    ]),

    # Main content
    html.Div(style=STYLES["main"], children=[
        # Upload zone
        dcc.Upload(
            id="upload-file",
            children=html.Div([
                html.Div("📂", style={"fontSize": "36px", "marginBottom": "8px"}),
                html.Div([
                    html.Span("Drag & drop", style={"fontWeight": "600"}),
                    html.Span(" your P&L file here, or ", style={"color": COLORS["text_muted"]}),
                    html.Span("browse", style={
                        "color": COLORS["primary"], "fontWeight": "600",
                        "textDecoration": "underline",
                    }),
                ]),
                html.P("Supports PDF, Excel (.xlsx), and CSV files",
                       style={"fontSize": "12px", "color": COLORS["text_muted"],
                              "marginTop": "4px"}),
            ]),
            style=STYLES["upload_zone"],
            multiple=False,
        ),

        # Status message
        html.Div(id="status-message", style={"marginBottom": "16px"}),

        # KPI cards row
        html.Div(id="kpi-cards", style=STYLES["kpi_grid"]),

        # Charts grid
        html.Div(id="charts-container", style=STYLES["chart_grid"], children=[
            html.Div(style=STYLES["chart_card"], children=[
                dcc.Graph(id="chart-revenue", config={"displayModeBar": False},
                          style={"height": "350px"}),
            ]),
            html.Div(style=STYLES["chart_card"], children=[
                dcc.Graph(id="chart-expense-pie", config={"displayModeBar": False},
                          style={"height": "350px"}),
            ]),
            html.Div(style=STYLES["chart_card"], children=[
                dcc.Graph(id="chart-waterfall", config={"displayModeBar": False},
                          style={"height": "350px"}),
            ]),
            html.Div(style=STYLES["chart_card"], children=[
                dcc.Graph(id="chart-margins", config={"displayModeBar": False},
                          style={"height": "350px"}),
            ]),
        ]),

        # RAG Chat panel
        html.Div(style=STYLES["chat_container"], children=[
            html.Div([
                html.Span("🤖 ", style={"fontSize": "18px"}),
                html.Span("AI Financial Analyst", style={
                    "fontWeight": "600", "fontSize": "16px"}),
                html.Span("  —  Ask questions about your P&L data",
                          style={"color": COLORS["text_muted"], "fontSize": "13px"}),
            ]),
            html.Div(id="chat-response", style={"display": "none"}),
            html.Div(style=STYLES["chat_input_area"], children=[
                dcc.Input(
                    id="chat-input",
                    type="text",
                    placeholder="e.g., Summarize this P&L, What are the major cost drivers?",
                    style=STYLES["chat_input"],
                    debounce=True,
                ),
                html.Button("Ask →", id="chat-send", style=STYLES["chat_button"]),
            ]),
        ]),
    ]),
])


# ── Callbacks ────────────────────────────────────────────────────────

@callback(
    [
        Output("kpi-cards", "children"),
        Output("chart-revenue", "figure"),
        Output("chart-expense-pie", "figure"),
        Output("chart-waterfall", "figure"),
        Output("chart-margins", "figure"),
        Output("status-message", "children"),
        Output("file-badge", "children"),
        Output("file-badge", "style"),
    ],
    Input("upload-file", "contents"),
    State("upload-file", "filename"),
    prevent_initial_call=True,
)
def on_file_upload(contents, filename):
    """
    Main callback: triggered when a file is uploaded.
    Runs the full pipeline and updates all dashboard components.
    """
    if contents is None:
        return no_update

    try:
        # Decode uploaded file
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # Save to temp file (parser expects a file path)
        ext = os.path.splitext(filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(decoded)
            tmp_path = tmp.name

        # ── Run pipeline ────────────────────────────────────────
        # Step 1: Parse
        df = ingest_document(tmp_path)

        # Step 2: Clean
        df = clean_pipeline(df)

        # Step 3: Compute KPIs
        kpis = extract_kpis(df)

        # Store state for RAG chat
        _state["df"] = df
        _state["kpis"] = kpis
        _state["filename"] = filename
        _state["chain_fn"] = None  # Reset chain (built lazily)

        # Clean up temp file
        os.unlink(tmp_path)

        # ── Generate visuals ────────────────────────────────────
        # KPI cards
        kpi_data = create_kpi_indicators(kpis)
        kpi_cards = _build_kpi_cards(kpi_data)

        # Charts
        fig_revenue = create_revenue_vs_expenses_bar(df)
        fig_pie = create_expense_breakdown_pie(df)
        fig_waterfall = create_waterfall_chart(df)
        fig_margins = create_margin_trend_line(kpis)

        # Status
        status = html.Div([
            html.Span("✅ ", style={"fontSize": "16px"}),
            html.Span(f"Successfully analyzed ", style={"color": COLORS["success"]}),
            html.Span(filename, style={"fontWeight": "600", "color": COLORS["text"]}),
            html.Span(f" — {len(df)} line items detected",
                      style={"color": COLORS["text_muted"]}),
        ], style={"fontSize": "14px"})

        # File badge
        badge = html.Span(f"📄 {filename}", style={
            "backgroundColor": COLORS["primary"] + "22",
            "color": COLORS["primary"],
            "padding": "6px 14px",
            "borderRadius": "20px",
            "fontSize": "13px",
            "fontWeight": "500",
        })
        badge_style = {"display": "block"}

        return kpi_cards, fig_revenue, fig_pie, fig_waterfall, fig_margins, status, badge, badge_style

    except Exception as e:
        error_msg = html.Div([
            html.Span("❌ ", style={"fontSize": "16px"}),
            html.Span(f"Error processing {filename}: {str(e)}",
                      style={"color": COLORS["danger"]}),
        ], style={"fontSize": "14px"})

        empty = go.Figure()
        empty.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

        return [], empty, empty, empty, empty, error_msg, "", {"display": "none"}


@callback(
    [
        Output("chat-response", "children"),
        Output("chat-response", "style"),
        Output("chat-input", "value"),
    ],
    Input("chat-send", "n_clicks"),
    State("chat-input", "value"),
    prevent_initial_call=True,
)
def on_chat_query(n_clicks, query):
    """
    RAG Chat callback: sends user query through the pipeline.
    Builds the RAG chain lazily on first query.
    """
    if not query or not query.strip():
        return no_update

    if _state["df"] is None:
        response_div = html.Div([
            html.Span("⚠️ ", style={"fontSize": "16px"}),
            "Please upload a P&L file first before asking questions.",
        ], style={**STYLES["chat_response"], "color": COLORS["warning"]})
        return response_div, {"display": "block"}, ""

    try:
        # Build RAG chain lazily on first query
        if _state["chain_fn"] is None:
            _state["chain_fn"] = _build_rag_chain(_state["df"])

        if _state["chain_fn"] is None:
            # No API key — provide KPI-based response only
            response_text = _fallback_response(query, _state["kpis"])
        else:
            from src.rag.pipeline import query_pipeline
            result = query_pipeline(_state["chain_fn"], query, _state["kpis"])
            response_text = result.raw_response

        response_div = html.Div([
            html.Div([
                html.Span("🤖 ", style={"fontSize": "14px"}),
                html.Span("AI Analyst", style={
                    "fontWeight": "600", "color": COLORS["primary"],
                    "fontSize": "13px",
                }),
            ], style={"marginBottom": "8px"}),
            html.Div(response_text, style={"color": COLORS["text"]}),
        ], style=STYLES["chat_response"])

        return response_div, {"display": "block"}, ""

    except Exception as e:
        error_div = html.Div([
            html.Span("❌ ", style={"fontSize": "14px"}),
            f"Error: {str(e)}",
        ], style={**STYLES["chat_response"], "color": COLORS["danger"]})
        return error_div, {"display": "block"}, ""


# ── Helpers ──────────────────────────────────────────────────────────

def _build_kpi_cards(kpi_data: list[dict]) -> list:
    """Build the KPI card HTML components."""
    cards = []
    for kpi in kpi_data:
        card = html.Div(style={
            **STYLES["kpi_card"],
            "borderTop": f"3px solid {kpi['color']}",
        }, children=[
            html.Div(kpi["icon"], style={"fontSize": "24px", "marginBottom": "4px"}),
            html.Div(kpi["formatted"], style={
                "fontSize": "28px",
                "fontWeight": "700",
                "color": kpi["color"],
                "letterSpacing": "-1px",
            }),
            html.Div(kpi["title"], style={
                "fontSize": "12px",
                "color": COLORS["text_muted"],
                "marginTop": "4px",
                "textTransform": "uppercase",
                "letterSpacing": "0.5px",
            }),
        ])
        cards.append(card)
    return cards


def _build_rag_chain(df: pd.DataFrame):
    """Build the RAG chain from the current DataFrame. Returns None if no API key."""
    try:
        from config import GOOGLE_API_KEY
        if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_google_api_key_here":
            print("[Dashboard] No valid API key — RAG chat disabled")
            return None

        from src.chunking.financial_chunker import chunk_document
        from src.vectorstore.store import build_vectorstore, get_retriever
        from src.rag.pipeline import build_rag_chain

        docs = chunk_document(df)
        vs = build_vectorstore(docs)
        retriever = get_retriever(vs)
        chain_fn = build_rag_chain(retriever)
        print("[Dashboard] RAG chain built successfully")
        return chain_fn

    except Exception as e:
        print(f"[Dashboard] Could not build RAG chain: {e}")
        return None


def _fallback_response(query: str, kpis: dict) -> str:
    """Generate a basic KPI-based response when RAG is unavailable."""
    lines = ["📊 **KPI Summary** (RAG unavailable — showing computed metrics):\n"]
    for key, value in kpis.items():
        if value is not None:
            label = key.replace("_", " ").title()
            if key.endswith("_pct"):
                lines.append(f"  • {label}: {value:.1f}%")
            else:
                lines.append(f"  • {label}: ${value:,.0f}")

    lines.append("\n💡 Set your GOOGLE_API_KEY in .env to enable AI-powered analysis.")
    return "\n".join(lines)


# ── Run Server ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  📊 P&L Analyzer Dashboard")
    print("  Open: http://127.0.0.1:8050")
    print("=" * 55 + "\n")
    app.run(debug=True, host="127.0.0.1", port=8050)
