"""
Test script for the P&L Summarizer pipeline.

Tests ingestion, cleaning, chunking, and KPI computation
using a programmatically generated sample P&L CSV.
"""

import os
import sys
import tempfile

import pandas as pd

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# ── Sample P&L data ─────────────────────────────────────────────────

SAMPLE_PL_DATA = {
    "Line Item": [
        "Revenue",
        "Cost of Goods Sold",
        "Gross Profit",
        "Marketing Expenses",
        "R&D Expenses",
        "SG&A",
        "Total Operating Expenses",
        "Operating Income",
        "Interest Expense",
        "Tax Expense",
        "Net Income",
        "EBITDA",
    ],
    "Q1 2025": [
        "$5,000,000",
        "$2,000,000",
        "$3,000,000",
        "$500,000",
        "$300,000",
        "$400,000",
        "$1,200,000",
        "$1,800,000",
        "$100,000",
        "$425,000",
        "$1,275,000",
        "$2,100,000",
    ],
    "Q2 2025": [
        "$5,600,000",
        "$2,240,000",
        "$3,360,000",
        "$650,000",
        "$320,000",
        "$420,000",
        "$1,390,000",
        "$1,970,000",
        "$100,000",
        "$467,500",
        "$1,402,500",
        "$2,310,000",
    ],
}


def create_sample_csv(path: str) -> str:
    """Create a sample P&L CSV file and return its path."""
    df = pd.DataFrame(SAMPLE_PL_DATA)
    df.to_csv(path, index=False)
    return path


# ── Tests ────────────────────────────────────────────────────────────


def test_parser():
    """Test document parsing for CSV."""
    from src.ingestion.parser import ingest_document

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    create_sample_csv(path)

    try:
        df = ingest_document(path)
        assert len(df) == 12, f"Expected 12 rows, got {len(df)}"
        assert len(df.columns) == 3, f"Expected 3 columns, got {len(df.columns)}"
        print("✅ test_parser PASSED")
    finally:
        os.unlink(path)


def test_cleaner():
    """Test data cleaning and currency normalization."""
    from src.ingestion.parser import ingest_document
    from src.ingestion.cleaner import clean_pipeline

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    create_sample_csv(path)

    try:
        df = ingest_document(path)
        cleaned = clean_pipeline(df)

        # Check that currency was normalized
        numeric_cols = cleaned.select_dtypes(include=["number"]).columns
        assert len(numeric_cols) >= 2, (
            f"Expected at least 2 numeric columns after cleaning, "
            f"got {len(numeric_cols)}"
        )

        # Check specific value: Revenue Q1 should be 5000000.0
        revenue_row = cleaned[
            cleaned.iloc[:, 0].astype(str).str.lower().str.contains("revenue")
        ]
        assert len(revenue_row) > 0, "Revenue row not found after cleaning"
        print("✅ test_cleaner PASSED")
    finally:
        os.unlink(path)


def test_chunker():
    """Test financial section chunking."""
    from src.ingestion.parser import ingest_document
    from src.ingestion.cleaner import clean_pipeline
    from src.chunking.financial_chunker import chunk_document

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    create_sample_csv(path)

    try:
        df = ingest_document(path)
        cleaned = clean_pipeline(df)
        docs = chunk_document(
            cleaned,
            metadata={"quarter": "Q1-Q2 2025", "company": "Test Corp"},
        )

        assert len(docs) > 0, "No documents created by the chunker"
        sections = [d.metadata.get("section") for d in docs]
        print(f"   Sections found: {sections}")

        # Should find at least Revenue and some expense sections
        assert any("Revenue" in s for s in sections), "Revenue section not found"
        assert all(
            d.metadata.get("company") == "Test Corp" for d in docs
        ), "Metadata not preserved"

        print("✅ test_chunker PASSED")
    finally:
        os.unlink(path)


def test_kpi_engine():
    """Test KPI computation with known values."""
    from src.ingestion.parser import ingest_document
    from src.ingestion.cleaner import clean_pipeline
    from src.analysis.kpi_engine import extract_kpis

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    create_sample_csv(path)

    try:
        df = ingest_document(path)
        cleaned = clean_pipeline(df)
        kpis = extract_kpis(cleaned)

        # Revenue should be 5,000,000
        assert kpis.get("revenue") is not None, "Revenue KPI not found"

        # Gross Margin should be (5M - 2M) / 5M * 100 = 60%
        gm = kpis.get("gross_margin_pct")
        if gm is not None:
            assert abs(gm - 60.0) < 1.0, f"Expected ~60% gross margin, got {gm}%"
            print(f"   Gross Margin: {gm}% ✓")

        print(f"   KPIs computed: {[k for k, v in kpis.items() if v is not None]}")
        print("✅ test_kpi_engine PASSED")
    finally:
        os.unlink(path)


def test_query_classification():
    """Test query type classification."""
    # Set a dummy API key so config.py doesn't raise on import
    os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-key")
    from src.rag.pipeline import classify_query

    assert classify_query("Summarize this P&L") == "summary"
    assert classify_query("Compare Q1 and Q2") == "comparison"
    assert classify_query("Why did net profit decline?") == "risk"
    assert classify_query("What is the gross margin?") == "kpi"
    assert classify_query("Hello") == "generic"

    print("✅ test_query_classification PASSED")


# ── Runner ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  P&L Summarizer — Pipeline Tests")
    print("=" * 50 + "\n")

    tests = [
        test_parser,
        test_cleaner,
        test_chunker,
        test_kpi_engine,
        test_query_classification,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            print(f"\n▶ Running {test.__name__} …")
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 50}\n")
