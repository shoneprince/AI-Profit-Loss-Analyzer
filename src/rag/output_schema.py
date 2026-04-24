"""
Structured Output Schema

Pydantic models defining the structured JSON response format
for the P&L Summarizer. Makes the pipeline API-ready.
"""

from pydantic import BaseModel, Field


class PLSummary(BaseModel):
    """Structured output for a P&L analysis response."""

    revenue_summary: str = Field(
        default="Not available",
        description="Summary of revenue trends and key figures.",
    )
    expense_summary: str = Field(
        default="Not available",
        description="Breakdown of major expense categories.",
    )
    profit_trend: str = Field(
        default="Not available",
        description="Analysis of profitability trends (margins, net income).",
    )
    risks: str = Field(
        default="Not available",
        description="Key risk indicators and concerns identified.",
    )
    kpis: dict = Field(
        default_factory=dict,
        description="Computed financial KPIs (from the KPI engine).",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Confidence in the analysis (0-1). Higher when more data "
            "points are available and cross-validated."
        ),
    )
    sources_used: list[str] = Field(
        default_factory=list,
        description="Sections of the document used for this analysis.",
    )
    raw_response: str = Field(
        default="",
        description="The full unstructured LLM response.",
    )
    hallucination_flags: list[str] = Field(
        default_factory=list,
        description=(
            "Warnings from post-generation verification. "
            "Flags number discrepancies and speculative language."
        ),
    )
