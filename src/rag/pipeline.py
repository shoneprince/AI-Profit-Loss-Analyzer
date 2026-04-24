"""
RAG Pipeline — Core Module

Builds the retrieval-augmented generation chain using:
- FAISS retriever (from vectorstore module)
- Gemini 3.1 Flash-Lite LLM (via langchain-google-genai)
- Financial prompts (from prompts module)
- Structured output (from output_schema module)

Uses LangChain Expression Language (LCEL) for chain composition.
"""

import json
import os
import re
import sys

from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE

from src.rag.prompts import get_prompt
from src.rag.output_schema import PLSummary


# ── Query Classification ─────────────────────────────────────────────

_QUERY_PATTERNS = {
    "summary": [
        "summarize", "summary", "overview", "tell me about",
        "what does this show", "explain this", "break down",
        "walk me through", "analyze",
    ],
    "comparison": [
        "compare", "comparison", "versus", "vs", "difference",
        "quarter over quarter", "qoq", "yoy", "year over year",
        "change between", "growth from",
    ],
    "risk": [
        "risk", "concern", "decline", "drop", "decrease",
        "warning", "red flag", "issue", "problem",
        "why did.*decline", "why did.*drop",
    ],
    "kpi": [
        "kpi", "metric", "margin", "ratio", "ebitda",
        "gross margin", "operating margin", "net margin",
        "cost ratio", "financial health",
    ],
}


def classify_query(query: str) -> str:
    """
    Classify a user query into a type for prompt selection.

    Uses simple keyword matching — fast and predictable.

    Args:
        query: The user's natural language question.

    Returns:
        Query type: 'summary', 'comparison', 'risk', 'kpi', or 'generic'.
    """
    query_lower = query.strip().lower()

    for query_type, patterns in _QUERY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return query_type

    return "generic"


# ── LLM Builder ──────────────────────────────────────────────────────

def _get_llm() -> ChatGoogleGenerativeAI:
    """Create the Gemini 3.1 Flash-Lite LLM instance."""
    return ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=LLM_TEMPERATURE,
    )


# ── Chain Builder (LCEL) ─────────────────────────────────────────────

def _format_docs(docs: list) -> str:
    """Format retrieved documents into a single context string."""
    return "\n\n".join(doc.page_content for doc in docs)


def build_rag_chain(retriever):
    """
    Build an LCEL-based RAG chain with Gemini 3.1 Flash-Lite.

    Returns a dict containing:
        - chain_fn:  callable(query, kpi_data) → (answer, source_docs)
        - retriever: the retriever for direct access
    """
    llm = _get_llm()

    def run_chain(query: str, kpi_data: dict | None = None):
        """Execute the RAG chain for a given query."""
        if kpi_data is None:
            kpi_data = {}

        # Retrieve relevant docs
        source_docs = retriever.invoke(query)

        # Format context
        context = _format_docs(source_docs)
        kpi_str = _format_kpis(kpi_data)

        # Get appropriate prompt
        query_type = classify_query(query)
        prompt = get_prompt(query_type)

        # Build and invoke the chain
        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke({
            "context": context,
            "question": query,
            "kpi_data": kpi_str,
        })

        return answer, source_docs

    return run_chain


# ── Post-generation verification ─────────────────────────────────────

_SPECULATIVE_PHRASES = [
    "it is likely", "probably", "may indicate", "could suggest",
    "typically", "generally", "in most industries", "industry average",
    "benchmark", "peer companies", "normally", "it appears that",
    "one might expect", "it is reasonable to assume",
]


def _verify_numbers(answer: str, kpi_data: dict) -> list[str]:
    """
    Cross-check percentages in the LLM answer against computed KPIs.
    Returns warning strings for discrepancies > 1 percentage point.
    """
    flags = []
    pct_matches = re.findall(r'(\d+\.?\d*)\s*%', answer)

    margin_kpis = {
        "gross_margin_pct": "gross margin",
        "operating_margin_pct": "operating margin",
        "net_margin_pct": "net margin",
        "ebitda_margin_pct": "ebitda margin",
        "cost_ratio_pct": "cost ratio",
    }

    for kpi_key, label in margin_kpis.items():
        expected = kpi_data.get(kpi_key)
        if expected is None:
            continue
        for pct_str in pct_matches:
            pct_val = float(pct_str)
            if abs(pct_val - expected) > 1.0 and abs(pct_val - expected) < 20:
                if label in answer.lower():
                    flags.append(
                        f"\u26a0 {label}: LLM said {pct_val}% but computed value is {expected}%"
                    )
    return flags


def _detect_speculation(answer: str) -> list[str]:
    """Flag speculative or ungrounded language in the LLM response."""
    flags = []
    answer_lower = answer.lower()
    for phrase in _SPECULATIVE_PHRASES:
        if phrase in answer_lower:
            flags.append(f"\u26a0 Speculative language detected: '{phrase}'")
    return flags


# ── Query Execution ──────────────────────────────────────────────────

def _estimate_confidence(
    kpi_data: dict,
    source_docs: list,
    hallucination_flags: list[str] | None = None,
) -> float:
    """
    Estimate a confidence score based on data availability.

    Heuristic:
    - More KPIs available → higher confidence
    - More source sections → higher confidence
    - Hallucination flags detected → lower confidence
    """
    kpi_count = sum(1 for v in kpi_data.values() if v is not None)
    max_kpis = 10

    section_count = len(set(
        doc.metadata.get("section", "") for doc in source_docs
    ))
    max_sections = 8

    kpi_score = min(kpi_count / max_kpis, 1.0) * 0.5
    section_score = min(section_count / max_sections, 1.0) * 0.5

    base = round(kpi_score + section_score, 2)

    # Penalise for each hallucination flag (max -0.4)
    if hallucination_flags:
        penalty = min(len(hallucination_flags) * 0.1, 0.4)
        base = max(round(base - penalty, 2), 0.05)

    return base


def query_pipeline(
    chain_fn,
    query: str,
    kpi_data: dict | None = None,
) -> PLSummary:
    """
    Execute a query through the RAG pipeline.

    Steps:
    1. Classify the query type
    2. Run the chain (retrieval + LLM)
    3. Package into structured output

    Args:
        chain_fn: The callable returned by build_rag_chain.
        query:    User's natural language question.
        kpi_data: Pre-computed KPIs from the KPI engine.

    Returns:
        A PLSummary object with structured results.
    """
    if kpi_data is None:
        kpi_data = {}

    query_type = classify_query(query)
    print(f"[RAG] Query classified as: {query_type}")

    # Run the chain
    answer, source_docs = chain_fn(query, kpi_data)

    # Post-generation verification
    number_flags = _verify_numbers(answer, kpi_data)
    speculation_flags = _detect_speculation(answer)
    all_flags = number_flags + speculation_flags

    if all_flags:
        print(f"[RAG] \u26a0 Hallucination flags: {all_flags}")

    # Extract sources
    sources_used = list(set(
        doc.metadata.get("section", "Unknown") for doc in source_docs
    ))

    # Estimate confidence (penalised by hallucination flags)
    confidence = _estimate_confidence(kpi_data, source_docs, all_flags)

    # Build structured output
    summary = PLSummary(
        revenue_summary=_extract_section(answer, "revenue"),
        expense_summary=_extract_section(answer, "expense"),
        profit_trend=_extract_section(answer, "profit"),
        risks=_extract_section(answer, "risk"),
        kpis=kpi_data,
        confidence_score=confidence,
        sources_used=sources_used,
        raw_response=answer,
        hallucination_flags=all_flags,
    )

    return summary


def _format_kpis(kpi_data: dict) -> str:
    """Format KPI dict as a readable string for prompt injection."""
    if not kpi_data:
        return "No KPIs computed (insufficient data)."

    lines = []
    for key, value in kpi_data.items():
        if value is None:
            continue
        if key.endswith("_pct"):
            label = key.replace("_pct", "").replace("_", " ").title()
            lines.append(f"  - {label}: {value}%")
        elif isinstance(value, (int, float)):
            label = key.replace("_", " ").title()
            lines.append(f"  - {label}: {value:,.2f}")
        # Skip non-numeric keys like latest_period

    return "\n".join(lines) if lines else "No KPIs available."


def _extract_section(text: str, keyword: str) -> str:
    """
    Try to extract a section from the LLM response by keyword.

    Looks for markdown headers containing the keyword, then
    captures text until the next header.
    """
    pattern = rf"(?:#+\s*|(?:\*\*)).*?{keyword}.*?(?:\*\*)?[\s:]*\n(.*?)(?=\n#+|\n\*\*|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(1).strip()

    paragraphs = text.split("\n\n")
    for para in paragraphs:
        if keyword.lower() in para.lower():
            return para.strip()

    return "See raw response for details."
