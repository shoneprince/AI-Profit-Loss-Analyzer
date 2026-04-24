"""
Pydantic request/response schemas for the P&L Analyzer API.
"""

from pydantic import BaseModel, Field


# ── Upload ───────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response after a successful file upload and pipeline run."""
    filename: str
    rows: int
    columns: int
    sections: list[str] = Field(default_factory=list)
    kpis: dict = Field(default_factory=dict)
    message: str = "File processed successfully"


# ── Query ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Request body for the RAG query endpoint."""
    question: str = Field(..., min_length=1, max_length=1000)


class QueryResponse(BaseModel):
    """Response from the RAG query endpoint."""
    question: str
    query_type: str
    answer: str
    revenue_summary: str = "Not available"
    expense_summary: str = "Not available"
    profit_trend: str = "Not available"
    risks: str = "Not available"
    confidence_score: float = 0.0
    sources_used: list[str] = Field(default_factory=list)
    kpis: dict = Field(default_factory=dict)
    hallucination_flags: list[str] = Field(default_factory=list)


# ── KPIs ─────────────────────────────────────────────────────────────

class KPIResponse(BaseModel):
    """Response from the KPI endpoint."""
    filename: str | None = None
    kpis: dict = Field(default_factory=dict)
    available_count: int = 0
    latest_period: str | None = None


# ── Chart Data ───────────────────────────────────────────────────────

class ChartSeries(BaseModel):
    """A single data series for a chart."""
    name: str
    labels: list[str] = Field(default_factory=list)
    values: list[float | None] = Field(default_factory=list)
    color: str | None = None


class ChartData(BaseModel):
    """Data for a single chart."""
    chart_type: str          # "bar", "pie", "waterfall", "gauge"
    title: str
    series: list[ChartSeries] = Field(default_factory=list)


class ChartDataResponse(BaseModel):
    """Response from the chart-data endpoint."""
    filename: str | None = None
    charts: list[ChartData] = Field(default_factory=list)


# ── Health ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    pipeline_ready: bool = False
    file_loaded: str | None = None


class DataPreviewResponse(BaseModel):
    """Response from the data-preview endpoint."""
    filename: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    total_rows: int = 0
