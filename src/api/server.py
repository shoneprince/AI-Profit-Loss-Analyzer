"""
P&L Analyzer — FastAPI Backend

REST API wrapping the full pipeline:
  POST /api/upload      → parse + clean + chunk + vectorise + KPIs
  POST /api/query       → RAG Q&A via Gemini
  GET  /api/kpis        → computed KPI metrics
  GET  /api/chart-data  → chart-ready JSON for all visualisations
  GET  /api/health      → health check

All keyword matching uses financial_keywords.py as a single source
of truth shared across server, kpi_engine, cleaner, and chunker.
"""

import os
import sys
import tempfile

import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# Ensure financial_keywords.py is findable regardless of invocation directory
_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in [PROJECT_ROOT, _SERVER_DIR,
           os.path.join(_SERVER_DIR, ".."),
           os.path.join(_SERVER_DIR, "..", "..")]:
    if os.path.exists(os.path.join(_p, "financial_keywords.py")):
        if _p not in sys.path:
            sys.path.insert(0, _p)
        break

from src.ingestion.parser import ingest_document
from src.ingestion.cleaner import clean_pipeline
from src.chunking.financial_chunker import chunk_document
from src.analysis.kpi_engine import extract_kpis
from src.api.schemas import (
    UploadResponse, QueryRequest, QueryResponse,
    KPIResponse, ChartDataResponse, ChartData, ChartSeries,
    HealthResponse, DataPreviewResponse,
)
from financial_keywords import (
    REVENUE_KEYWORDS,
    COGS_KEYWORDS,
    INVENTORY_CHANGE_KEYWORDS,
    EMPLOYEE_COST_KEYWORDS,
    DEPRECIATION_KEYWORDS,
    FINANCE_COST_KEYWORDS,
    SGA_KEYWORDS,
    MARKETING_KEYWORDS,
    RD_KEYWORDS,
    OTHER_EXPENSE_KEYWORDS,
    TOTAL_OPEX_KEYWORDS,
    NET_INCOME_KEYWORDS,
    TAX_KEYWORDS,
    OPERATING_INCOME_KEYWORDS,
    SKIP_ROW_KEYWORDS,
    PBT_KEYWORDS,
)


# ── App setup ────────────────────────────────────────────────────────

app = FastAPI(
    title="P&L Analyzer API",
    description="RAG-powered Profit & Loss analyzer",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-profit-loss-analyzer.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import threading

_state_lock = threading.Lock()
# In-process session state.  Lost on server restart; safe for single-user
# or low-concurrency usage. For multi-worker deployments, swap for Redis.
_state: dict = {
    "df": None,
    "kpis": {},
    "chain_fn": None,
    "filename": None,
    "sections": [],
}


# ── Shared DataFrame helpers ─────────────────────────────────────────

def _get_label_col(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if df[col].dtype == object:
            return col
    return None


def _get_numeric_cols(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["number"]).columns.tolist()


def _find_row_values(df: pd.DataFrame, keywords: list[str]) -> dict[str, float | None]:
    """
    Find the first row whose label matches any keyword (keyword in label).

    Uses only the forward direction (keyword in label) to avoid false positives
    such as short keyword "pat" matching the header row "particulars".
    Also skips metadata/header rows via SKIP_ROW_KEYWORDS.

    Row selection priority: "Total …" rows are checked first so that aggregate
    lines (e.g. "Total Revenue from operations") are preferred over component
    lines (e.g. "Interest Income") when the caller needs a single value.

    Returns {column_name: value} for all numeric columns.
    """
    label_col = _get_label_col(df)
    num_cols = _get_numeric_cols(df)
    if not label_col or not num_cols:
        return {}

    kw_lower = [k.lower() for k in keywords]
    skip_lower = [s.lower() for s in SKIP_ROW_KEYWORDS]

    # Tier 0: rows starting with "total" that match a keyword — highest priority.
    # This ensures "Total Revenue from operations" (805.56) is always preferred
    # over component rows like "Interest Income" (117.13) even when those
    # component labels are exact keyword matches.
    def _score(label: str) -> int:
        ll = label.strip().lower()
        if any(skip in ll for skip in skip_lower):
            return -1
        if not any(kw in ll for kw in kw_lower):
            return -1
        return 2 if ll.startswith("total") else 1

    rows_by_priority = sorted(
        [(i, row) for i, row in df.iterrows() if _score(str(row[label_col])) > 0],
        key=lambda x: _score(str(x[1][label_col])),
        reverse=True,
    )

    for _, row in rows_by_priority:
        val = row.get(num_cols[0]) if num_cols else None
        # Try each numeric col in order (latest period first)
        for col in num_cols:
            v = row.get(col)
            if v is not None and pd.notna(v):
                return {
                    c: (float(row[c]) if pd.notna(row[c]) else None)
                    for c in num_cols
                }
    return {}


def _first_val(row_vals: dict, num_cols: list[str]) -> float | None:
    """Return the value from the first (latest) numeric column."""
    for col in num_cols:
        v = row_vals.get(col)
        if v is not None:
            return v
    return None


def _latest_col(num_cols: list[str]) -> str | None:
    """
    Return the column most likely to represent the latest/current period.
    Indian financial statements put the most recent year FIRST (left column).
    Falls back to num_cols[0] if no year can be detected.
    """
    import re
    if not num_cols:
        return None
    best_col, best_year = num_cols[0], -1
    for col in num_cols:
        years = re.findall(r"20\d{2}", str(col))
        if years:
            y = max(int(y) for y in years)
            if y > best_year:
                best_year, best_col = y, col
    return best_col


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        pipeline_ready=_state["df"] is not None,
        file_loaded=_state["filename"],
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    quarter: str | None = Form(None),
    company: str | None = Form(None),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".pdf", ".xlsx", ".xls", ".csv"}:
        raise HTTPException(400, f"Unsupported format: '{ext}'")

    tmp_path = ""
    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        df = ingest_document(tmp_path)
        df = clean_pipeline(df)

        metadata = {}
        if quarter:
            metadata["quarter"] = quarter
        if company:
            metadata["company"] = company

        documents = chunk_document(df, metadata)
        sections = list({d.metadata.get("section", "Unknown") for d in documents})
        kpis = extract_kpis(df)
        chain_fn = _try_build_rag_chain(documents)

        with _state_lock:
            _state.update(df=df, kpis=kpis, chain_fn=chain_fn,
                          filename=file.filename, sections=sections)

        return UploadResponse(
            filename=file.filename,
            rows=len(df),
            columns=len(df.columns),
            sections=sections,
            kpis={k: v for k, v in kpis.items() if v is not None},
            message=f"Successfully processed {file.filename}",
        )

    except ValueError as ve:
        msg = str(ve)
        code = 429 if any(x in msg for x in ("RESOURCE_EXHAUSTED", "quota", "429")) else 400
        raise HTTPException(code, msg)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Pipeline error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    if _state["df"] is None:
        raise HTTPException(400, "No document loaded. Upload a file first.")
    if _state["chain_fn"] is None:
        raise HTTPException(503, "RAG unavailable. Check GOOGLE_API_KEY in .env")

    try:
        from src.rag.pipeline import query_pipeline, classify_query
        query_type = classify_query(request.question)
        result = query_pipeline(_state["chain_fn"], request.question, _state["kpis"])
        return QueryResponse(
            question=request.question,
            query_type=query_type,
            answer=result.raw_response,
            revenue_summary=result.revenue_summary,
            expense_summary=result.expense_summary,
            profit_trend=result.profit_trend,
            risks=result.risks,
            confidence_score=result.confidence_score,
            sources_used=result.sources_used,
            kpis={k: v for k, v in result.kpis.items() if v is not None},
            hallucination_flags=getattr(result, "hallucination_flags", []),
        )
    except Exception as e:
        raise HTTPException(500, f"Query error: {e}")


@app.get("/api/kpis", response_model=KPIResponse)
async def get_kpis():
    if _state["df"] is None:
        raise HTTPException(400, "No document loaded.")
    available = {k: v for k, v in _state["kpis"].items() if v is not None}
    return KPIResponse(
        filename=_state["filename"],
        kpis=available,
        available_count=len(available),
        latest_period=_state["kpis"].get("latest_period"),
    )


@app.get("/api/data-preview", response_model=DataPreviewResponse)
async def get_data_preview():
    """Return the first 30 rows of the cleaned DataFrame for transparency."""
    if _state["df"] is None:
        raise HTTPException(400, "No document loaded.")
    df = _state["df"]
    preview = df.head(30).copy()
    # Convert to JSON-safe types
    for col in preview.select_dtypes(include=["number"]).columns:
        preview[col] = preview[col].apply(lambda v: round(float(v), 2) if pd.notna(v) else None)
    return DataPreviewResponse(
        filename=_state["filename"],
        columns=list(preview.columns),
        rows=preview.to_dict(orient="records"),
        total_rows=len(df),
    )


@app.get("/api/chart-data", response_model=ChartDataResponse)
async def get_chart_data():
    if _state["df"] is None:
        raise HTTPException(400, "No document loaded.")

    df, kpis = _state["df"], _state["kpis"]
    return ChartDataResponse(
        filename=_state["filename"],
        charts=[
            _build_revenue_vs_expenses(df),
            _build_expense_breakdown(df),
            _build_waterfall(df),
            _build_margin_chart(kpis),
        ],
    )


# ── Chart builders ───────────────────────────────────────────────────

def _build_revenue_vs_expenses(df: pd.DataFrame) -> ChartData:
    """
    Grouped bar chart: Revenue, Material/COGS, Total Expenses, Net Income.
    Each bar group = one period column; bars within group = metric type.
    """
    items = {
        "Revenue":        REVENUE_KEYWORDS,
        "Material/COGS":  COGS_KEYWORDS + INVENTORY_CHANGE_KEYWORDS,
        "Total Expenses": TOTAL_OPEX_KEYWORDS,
        "Net Income":     NET_INCOME_KEYWORDS,
    }
    colors = ["#6366f1", "#ef4444", "#f59e0b", "#22c55e"]
    num_cols = _get_numeric_cols(df)

    series = []
    for i, (name, keywords) in enumerate(items.items()):
        vals = _find_row_values(df, keywords)
        if vals:
            series.append(ChartSeries(
                name=name,
                labels=num_cols,
                values=[vals.get(c) for c in num_cols],
                color=colors[i],
            ))

    return ChartData(chart_type="bar", title="Revenue vs Key Expenses", series=series)


def _build_expense_breakdown(df: pd.DataFrame) -> ChartData:
    """
    Donut chart: individual expense line items for the latest period.

    Uses the full vocabulary from financial_keywords.py so any
    expense label present in any financial document format will match.
    """
    # Named expense categories with their keyword lists
    categories: dict[str, list[str]] = {
        "Material / COGS":   COGS_KEYWORDS + INVENTORY_CHANGE_KEYWORDS,
        "Employee Costs":    EMPLOYEE_COST_KEYWORDS,
        "Depreciation":      DEPRECIATION_KEYWORDS,
        "Finance Costs":     FINANCE_COST_KEYWORDS,
        "SG&A":              SGA_KEYWORDS,
        "Marketing":         MARKETING_KEYWORDS,
        "R&D":               RD_KEYWORDS,
        "Tax":               TAX_KEYWORDS,
        "Other Expenses":    OTHER_EXPENSE_KEYWORDS,
    }

    num_cols = _get_numeric_cols(df)
    latest = _latest_col(num_cols)
    if not latest:
        return ChartData(chart_type="pie", title="Expense Breakdown", series=[])

    labels, values = [], []
    seen_rows: set = set()   # prevent double-counting when a row matches
                              # multiple categories (e.g. "finance costs" & "interest")

    for name, keywords in categories.items():
        kw_lower = [k.lower() for k in keywords]
        label_col = _get_label_col(df)
        if not label_col:
            continue

        skip_lower = [s.lower() for s in SKIP_ROW_KEYWORDS]
        for idx, row in df.iterrows():
            if idx in seen_rows:
                continue
            row_label = str(row[label_col]).strip().lower()
            if any(skip in row_label for skip in skip_lower):
                continue
            if any(kw in row_label for kw in kw_lower):
                val = row.get(latest) if latest in row.index else None
                if val is not None and pd.notna(val) and abs(float(val)) > 0:
                    labels.append(name)
                    values.append(abs(float(val)))
                    seen_rows.add(idx)
                    break   # one row per category is enough

    series = [ChartSeries(name="Expenses", labels=labels, values=values)] if labels else []
    return ChartData(
        chart_type="pie",
        title=f"Expense Breakdown ({latest})",
        series=series,
    )


def _build_waterfall(df: pd.DataFrame) -> ChartData:
    """
    P&L Bridge waterfall: Revenue → deductions → Net Income.

    Steps use the central keyword lists so all known label formats
    for each line item are covered automatically.
    """
    steps: list[tuple[str, list[str], bool]] = [
        # (display_name, keyword_list, is_absolute)
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

    num_cols = _get_numeric_cols(df)
    latest = _latest_col(num_cols)
    if not latest:
        return ChartData(chart_type="waterfall", title="P&L Bridge", series=[])

    labels, values = [], []
    for name, keywords, is_absolute in steps:
        row_vals = _find_row_values(df, keywords)
        val = _first_val(row_vals, num_cols)
        if val is not None:
            labels.append(name)
            values.append(val if is_absolute else -abs(val))

    series = [ChartSeries(name="P&L Bridge", labels=labels, values=values)] if labels else []
    return ChartData(chart_type="waterfall", title=f"P&L Bridge ({latest})", series=series)


def _build_margin_chart(kpis: dict) -> ChartData:
    """Horizontal bar / gauge chart for all margin KPIs."""
    margin_keys = [
        ("Gross Margin",      "gross_margin_pct"),
        ("Operating Margin",  "operating_margin_pct"),
        ("Net Margin",        "net_margin_pct"),
        ("EBITDA Margin",     "ebitda_margin_pct"),
        ("Cost Ratio",        "cost_ratio_pct"),
    ]
    labels, values = [], []
    for name, key in margin_keys:
        v = kpis.get(key)
        if v is not None:
            labels.append(name)
            values.append(v)

    series = [ChartSeries(name="Margins (%)", labels=labels, values=values)] if labels else []
    return ChartData(chart_type="gauge", title="Margin Analysis", series=series)


# ── RAG chain builder ────────────────────────────────────────────────

def _try_build_rag_chain(documents):
    try:
        from config import GOOGLE_API_KEY
        if not GOOGLE_API_KEY:
            print("[API] No API key — RAG disabled")
            return None

        from src.vectorstore.store import build_vectorstore, get_retriever
        from src.rag.pipeline import build_rag_chain

        vs = build_vectorstore(documents)
        retriever = get_retriever(vs)
        chain_fn = build_rag_chain(retriever)
        print("[API] RAG chain ready")
        return chain_fn

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[API] RAG chain failed: {e}")
        return None


# ── Static files ─────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ── Dev server ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 50)
    print("  P&L Analyzer  |  http://127.0.0.1:8000")
    print("  API Docs      |  http://127.0.0.1:8000/docs")
    print("=" * 50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
